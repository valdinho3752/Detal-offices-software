from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Cita, EstadoCitaEnum, Usuario, Doctor, RolCodigoEnum, AuditoriaLog, AuditoriaAccionEnum
from app.core.dependencies import get_current_user
from app.schemas.cita import CitaCreate, CitaUpdate, CitaSillonControl, CitaResponse
from app.services.tratamiento_clinico import registrar_tratamiento_realizado

router = APIRouter(prefix="/citas", tags=["Agenda y Citas Dentales"])

# Estas citas ya no ocupan el horario del doctor.
ESTADOS_SIN_RESERVA = (EstadoCitaEnum.CANCELADA, EstadoCitaEnum.NO_ASISTIO)

@router.get("/", response_model=List[CitaResponse])
def listar_citas(
    doctor_id: Optional[UUID] = None,
    paciente_id: Optional[UUID] = None,
    tratamiento_id: Optional[UUID] = None,
    categoria: Optional[str] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    fecha_inicio: Optional[datetime] = None,
    fecha_fin: Optional[datetime] = None,
    estado: Optional[EstadoCitaEnum] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    desde = fecha_desde or fecha_inicio
    hasta = fecha_hasta or fecha_fin
    query = db.query(Cita)
    if doctor_id:
        query = query.filter(Cita.doctor_id == doctor_id)
    if paciente_id:
        query = query.filter(Cita.paciente_id == paciente_id)
    if tratamiento_id:
        query = query.filter(Cita.tratamiento_id == tratamiento_id)
    if categoria:
        from app.models.tratamiento import CatalogoTratamiento
        query = query.join(Cita.tratamiento).filter(CatalogoTratamiento.categoria == categoria)
    if desde:
        query = query.filter(Cita.fecha_inicio_programada >= desde)
    if hasta:
        if hasta.hour == 0 and hasta.minute == 0 and hasta.second == 0:
            hasta = hasta.replace(hour=23, minute=59, second=59, microsecond=999999)
        query = query.filter(Cita.fecha_fin_programada <= hasta)
    if estado:
        query = query.filter(Cita.estado == estado)

    return query.order_by(Cita.fecha_inicio_programada).all()

@router.post("/", response_model=CitaResponse, status_code=status.HTTP_201_CREATED)
def agendar_cita(
    datos: CitaCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doctor_obj = None
    if datos.doctor_id:
        doctor_obj = db.query(Doctor).filter(
            (Doctor.id == datos.doctor_id) | (Doctor.usuario_id == datos.doctor_id)
        ).first()

    rol_str = str(current_user.rol.codigo.value if hasattr(current_user.rol.codigo, "value") else current_user.rol.codigo).upper() if current_user.rol else ""

    resolved_doctor_id = None
    if rol_str in ["ADMIN", "RECEPCION", "RECEPCIONISTA"]:
        if doctor_obj:
            resolved_doctor_id = doctor_obj.id
        elif current_user.doctor_perfil:
            resolved_doctor_id = current_user.doctor_perfil.id
        else:
            primer_doc = db.query(Doctor).first()
            if primer_doc:
                resolved_doctor_id = primer_doc.id
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Debes especificar un doctor válido para agendar la cita"
                )
    else:
        if not current_user.doctor_perfil:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo personal médico o recepción pueden agendar citas"
            )
        resolved_doctor_id = current_user.doctor_perfil.id
        if doctor_obj and doctor_obj.id != current_user.doctor_perfil.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para agendar citas para otros doctores"
            )

    resolved_tratamiento_id = datos.tratamiento_id
    if not resolved_tratamiento_id and datos.item_plan_id:
        from app.models.tratamiento import ItemPlanTratamiento
        item = db.query(ItemPlanTratamiento).filter_by(id=datos.item_plan_id).first()
        if item and item.tratamiento_id:
            resolved_tratamiento_id = item.tratamiento_id

    motivo = datos.motivo_consulta
    if resolved_tratamiento_id:
        from app.models.tratamiento import CatalogoTratamiento
        trat = db.query(CatalogoTratamiento).filter_by(id=resolved_tratamiento_id).first()
        if trat and (not motivo or motivo == "Consulta Odontológica General"):
            motivo = trat.nombre

    if not datos.fecha_inicio_programada or not datos.fecha_fin_programada:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes indicar la fecha y hora de inicio y fin de la cita"
        )

    nueva_cita = Cita(
        paciente_id=datos.paciente_id,
        doctor_id=resolved_doctor_id,
        item_plan_id=datos.item_plan_id,
        tratamiento_id=resolved_tratamiento_id,
        fecha_inicio_programada=datos.fecha_inicio_programada,
        fecha_fin_programada=datos.fecha_fin_programada,
        motivo_consulta=motivo,
        notas_adicionales=datos.notas_adicionales,
        created_by_usuario_id=current_user.id
    )
    db.add(nueva_cita)
    db.flush()
    db.refresh(nueva_cita)
    _validar_horario_cita(nueva_cita, db)
    db.commit()
    db.refresh(nueva_cita)
    return nueva_cita

def _validar_horario_cita(cita: Cita, db: Session):
    """Comprueba que el horario sea coherente y que el doctor no tenga otra cita en ese rango."""
    if cita.fecha_fin_programada <= cita.fecha_inicio_programada:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La hora de fin de la cita debe ser posterior a la hora de inicio"
        )

    # El bloqueo evita que dos peticiones simultáneas reserven el mismo horario.
    db.query(Doctor).filter(Doctor.id == cita.doctor_id).with_for_update().first()
    conflicto = db.query(Cita).filter(
        Cita.doctor_id == cita.doctor_id,
        Cita.id != cita.id,
        Cita.estado.notin_(ESTADOS_SIN_RESERVA),
        Cita.fecha_inicio_programada < cita.fecha_fin_programada,
        Cita.fecha_fin_programada > cita.fecha_inicio_programada,
    ).first()
    if conflicto:
        inicio = conflicto.fecha_inicio_programada.strftime("%d/%m/%Y %H:%M")
        fin = conflicto.fecha_fin_programada.strftime("%H:%M")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El doctor ya tiene una cita de {inicio} a {fin}. Elige otro horario."
        )

def _finalizar_tratamientos_cita(cita: Cita, db: Session):
    """
    Sincroniza el plan de tratamiento y odontograma cuando la cita finaliza:
    marca los ítems asignados (cita.item_plan_id y los incluidos en notas_adicionales)
    como COMPLETADO y los registra en el odontograma de evolución del paciente.
    """
    from app.models.tratamiento import ItemPlanTratamiento
    from app.models.enums import EstadoItemPlanEnum
    import re

    item_ids = []
    if cita.item_plan_id:
        item_ids.append(cita.item_plan_id)
    if cita.notas_adicionales:
        matches = re.findall(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', cita.notas_adicionales)
        for m in matches:
            uid = UUID(m)
            if uid not in item_ids:
                item_ids.append(uid)

    for iid in item_ids:
        item = db.query(ItemPlanTratamiento).filter_by(id=iid).first()
        if not item:
            continue
        item.estado = EstadoItemPlanEnum.COMPLETADO
        registrar_tratamiento_realizado(cita.paciente_id, cita.doctor_id, item, db)
    db.flush()

@router.put("/{id}", response_model=CitaResponse)
def actualizar_cita(
    id: UUID,
    datos: CitaUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cita = db.query(Cita).filter(Cita.id == id).first()
    if not cita:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")

    update_dict = datos.model_dump(exclude_unset=True)
    if "doctor_id" in update_dict and update_dict["doctor_id"] is not None:
        target_doc = update_dict["doctor_id"]
        doctor_obj = db.query(Doctor).filter(
            (Doctor.id == target_doc) | (Doctor.usuario_id == target_doc)
        ).first()

        rol_str = str(current_user.rol.codigo.value if hasattr(current_user.rol.codigo, "value") else current_user.rol.codigo).upper() if current_user.rol else ""

        if rol_str in ["ADMIN", "RECEPCION", "RECEPCIONISTA"]:
            if not doctor_obj:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor no encontrado")
            update_dict["doctor_id"] = doctor_obj.id
        else:
            if not current_user.doctor_perfil or (doctor_obj and doctor_obj.id != current_user.doctor_perfil.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Solo administradores o recepción pueden reasignar citas a otros doctores"
                )
            update_dict["doctor_id"] = current_user.doctor_perfil.id

    horario_previo = (cita.doctor_id, cita.fecha_inicio_programada, cita.fecha_fin_programada)
    estado_previo = cita.estado

    valid_fields = {
        "paciente_id", "doctor_id", "item_plan_id", "tratamiento_id",
        "fecha_inicio_programada", "fecha_fin_programada",
        "motivo_consulta", "notas_adicionales", "estado"
    }
    for field, value in update_dict.items():
        if field in valid_fields:
            setattr(cita, field, value)

    db.flush()
    db.refresh(cita)
    horario_actual = (cita.doctor_id, cita.fecha_inicio_programada, cita.fecha_fin_programada)
    # Solo se valida si cambió el horario o si se reactiva una cita que no ocupaba lugar:
    # cambiar el estado de una cita existente no debe bloquearse por datos antiguos.
    if cita.estado not in ESTADOS_SIN_RESERVA and (
        horario_actual != horario_previo or estado_previo in ESTADOS_SIN_RESERVA
    ):
        _validar_horario_cita(cita, db)

    # Si la cita pasa a FINALIZADA, actualizar tratamientos a Alta Clinica (Azul)
    if update_dict.get("estado") in [EstadoCitaEnum.FINALIZADA, "FINALIZADA"]:
        _finalizar_tratamientos_cita(cita, db)

    db.commit()
    db.refresh(cita)
    return cita

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def cancelar_cita(
    id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancela la cita sin borrarla: libera el horario y conserva el registro para el
    historial del paciente y las estadísticas de ausentismo.
    """
    cita = db.query(Cita).filter(Cita.id == id).first()
    if not cita:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    if cita.estado == EstadoCitaEnum.FINALIZADA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede cancelar una cita que ya fue atendida"
        )

    estado_previo = cita.estado.value
    cita.estado = EstadoCitaEnum.CANCELADA
    db.add(AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="citas",
        registro_id=cita.id,
        accion=AuditoriaAccionEnum.UPDATE,
        seccion_consultada="CANCELAR_CITA",
        datos_previos={"estado": estado_previo},
        datos_nuevos={"estado": EstadoCitaEnum.CANCELADA.value}
    ))
    db.commit()
    return None

@router.patch("/{id}/sillon", response_model=CitaResponse)
def controlar_tiempo_sillon(
    id: UUID,
    control: CitaSillonControl,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Control en tiempo real del paciente en el sillon dental:
    - hora_llegada_recepcion: cuando el paciente llega a la sala de espera.
    - hora_inicio_sillon: cuando entra al box y se sienta (estado EN_SILLON).
    - hora_fin_sillon: cuando se levanta al terminar (estado FINALIZADA).
    El trigger de PostgreSQL calcula automaticamente duracion_sillon_minutos.
    """
    cita = db.query(Cita).filter(Cita.id == id).first()
    if not cita:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")

    for field, value in control.model_dump(exclude_unset=True).items():
        setattr(cita, field, value)

    # Si la cita pasa a FINALIZADA en sillon, actualizar tratamientos a Alta Clinica (Azul)
    if control.estado in [EstadoCitaEnum.FINALIZADA, "FINALIZADA"]:
        _finalizar_tratamientos_cita(cita, db)

    db.commit()
    db.refresh(cita)
    return cita
