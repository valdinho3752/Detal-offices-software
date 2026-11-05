from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    VisitaEvolucion, ItemPlanTratamiento, EstadoItemPlanEnum,
    Usuario, AuditoriaLog, AuditoriaAccionEnum, Doctor
)
from app.core.dependencies import get_current_user
from app.services.tratamiento_clinico import registrar_tratamiento_realizado
from app.schemas.visita import (
    VisitaEvolucionCreate, VisitaEvolucionUpdate, VisitaEvolucionResponse
)

router = APIRouter(prefix="/visitas", tags=["Historia Clínica y Evoluciones Diarias"])

@router.get("/", response_model=List[VisitaEvolucionResponse])
def listar_visitas(
    paciente_id: Optional[UUID] = None,
    doctor_id: Optional[UUID] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(VisitaEvolucion)
    if paciente_id:
        query = query.filter(VisitaEvolucion.paciente_id == paciente_id)
    if doctor_id:
        query = query.filter(VisitaEvolucion.doctor_id == doctor_id)
    return query.order_by(VisitaEvolucion.fecha_hora.desc()).all()

@router.post("/", response_model=VisitaEvolucionResponse, status_code=status.HTTP_201_CREATED)
def registrar_visita_evolucion(
    datos: VisitaEvolucionCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Registra la atención dental de hoy:
    - Marca el ítem ejecutado hoy como COMPLETADO y actualiza el odontograma a azul (#3B82F6).
    - Marca el próximo ítem planificado como PROXIMA_SESION para la siguiente cita.
    """
    visita_dict = datos.model_dump()
    if not visita_dict.get("motivo_visita"):
        visita_dict["motivo_visita"] = visita_dict.get("motivo_consulta") or "Atención Odontológica"
    if not visita_dict.get("recomendaciones"):
        visita_dict["recomendaciones"] = visita_dict.get("observaciones_clinicas")
    if not visita_dict.get("indicaciones_proxima_visita"):
        visita_dict["indicaciones_proxima_visita"] = visita_dict.get("indicaciones_postoperatorias")
    visita_dict.pop("motivo_consulta", None)
    visita_dict.pop("observaciones_clinicas", None)
    visita_dict.pop("indicaciones_postoperatorias", None)

    es_admin = current_user.rol and str(current_user.rol.codigo).upper() == "ADMIN"
    doctor = None

    if es_admin:
        if visita_dict.get("doctor_id"):
            doctor = db.query(Doctor).filter((Doctor.id == visita_dict["doctor_id"]) | (Doctor.usuario_id == visita_dict["doctor_id"])).first()
        if not doctor and current_user.doctor_perfil:
            doctor = current_user.doctor_perfil
        if not doctor:
            doctor = db.query(Doctor).first()
        if not doctor:
            doctor = Doctor(usuario_id=current_user.id, especialidad="Odontología General / Dirección Médica")
            db.add(doctor)
            db.flush()
    else:
        if not current_user.doctor_perfil:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: solo personal médico o administradores pueden registrar visitas de evolución"
            )
        doctor = current_user.doctor_perfil

    visita_dict["doctor_id"] = doctor.id
    visita = VisitaEvolucion(**visita_dict)
    db.add(visita)
    db.flush()

    # Actualizar estado del ítem realizado hoy y sincronizar odontograma
    if datos.item_plan_id:
        item_hoy = db.query(ItemPlanTratamiento).filter(ItemPlanTratamiento.id == datos.item_plan_id).first()
        if item_hoy:
            item_hoy.estado = EstadoItemPlanEnum.COMPLETADO
            registrar_tratamiento_realizado(visita.paciente_id, visita.doctor_id, item_hoy, db)

    # Marcar el ítem de la siguiente cita como PROXIMA_SESION
    if datos.proximo_item_plan_id:
        item_prox = db.query(ItemPlanTratamiento).filter(ItemPlanTratamiento.id == datos.proximo_item_plan_id).first()
        if item_prox:
            item_prox.estado = EstadoItemPlanEnum.PROXIMA_SESION
            if hasattr(item_prox, 'es_proxima_sesion'):
                item_prox.es_proxima_sesion = True

    # Log de auditoría
    log = AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="visitas_evolucion",
        registro_id=visita.id,
        accion=AuditoriaAccionEnum.INSERT,
        seccion_consultada="REGISTRO_ATENCION_EVOLUCION"
    )
    db.add(log)
    db.commit()
    db.refresh(visita)
    return visita

@router.get("/{id}", response_model=VisitaEvolucionResponse)
def obtener_visita(
    id: UUID,
    request: Request,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    visita = db.query(VisitaEvolucion).filter(VisitaEvolucion.id == id).first()
    if not visita:
        raise HTTPException(status_code=404, detail="Visita clínica no encontrada")

    # Auditoría de visualización médica (VIEW)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    log = AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="visitas_evolucion",
        registro_id=visita.id,
        accion=AuditoriaAccionEnum.VIEW,
        seccion_consultada="HISTORIA_CLINICA_SESION",
        ip_origen=client_ip,
        user_agent=user_agent
    )
    db.add(log)
    db.commit()

    return visita

@router.put("/{id}", response_model=VisitaEvolucionResponse)
def actualizar_visita(
    id: UUID,
    datos: VisitaEvolucionUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    visita = db.query(VisitaEvolucion).filter(VisitaEvolucion.id == id).first()
    if not visita:
        raise HTTPException(status_code=404, detail="Visita clínica no encontrada")

    update_data = datos.model_dump(exclude_unset=True)
    es_admin = current_user.rol and str(current_user.rol.codigo).upper() == "ADMIN"

    if "doctor_id" in update_data and update_data["doctor_id"]:
        if not es_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores pueden reasignar el doctor de la visita clínica"
            )
        doc = db.query(Doctor).filter((Doctor.id == update_data["doctor_id"]) | (Doctor.usuario_id == update_data["doctor_id"])).first()
        if doc:
            update_data["doctor_id"] = doc.id

    for field, value in update_data.items():
        setattr(visita, field, value)
    db.commit()
    db.refresh(visita)
    return visita
