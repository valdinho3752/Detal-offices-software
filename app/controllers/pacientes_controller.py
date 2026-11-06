from datetime import datetime, timezone
from typing import List, Literal, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.database import get_db
from app.models import (
    Paciente, AntecedenteMedico, AuditoriaLog, AuditoriaAccionEnum,
    Pago, Usuario
)
from app.core.dependencies import require_permission
from app.models.enums import EstadoRegistroEnum
from app.services.inactividad_pacientes import (
    consulta_con_ultima_cita, describir_filas, describir_uno, filtro_activos, filtro_inactivos,
)
from app.services.saldos import calcular_saldo_paciente
from app.schemas.paciente import (
    PacienteCreate, PacienteUpdate, PacienteResponse,
    AntecedenteMedicoUpdate, AntecedenteMedicoResponse
)

router = APIRouter(prefix="/pacientes", tags=["Pacientes y Ficha Médica"])

@router.get("/", response_model=List[PacienteResponse])
def listar_pacientes(
    q: Optional[str] = Query(None, description="Buscar por nombre, apellido o documento"),
    estado: Optional[Literal["ACTIVO", "INACTIVO"]] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: Usuario = Depends(require_permission("PACIENTES_READ")),
    db: Session = Depends(get_db)
):
    query, ultima = consulta_con_ultima_cita(db)
    if estado == "INACTIVO":
        query = query.filter(filtro_inactivos(ultima, db))
    elif estado == "ACTIVO":
        query = query.filter(filtro_activos(ultima, db))
    if q:
        search = f"%{q}%"
        query = query.filter(
            or_(
                func.concat(Paciente.nombres, ' ', Paciente.apellidos).ilike(search),
                Paciente.numero_documento.ilike(search),
                Paciente.telefono.ilike(search),
            )
        )
    return describir_filas(query.order_by(Paciente.apellidos).offset(skip).limit(limit).all(), db)

@router.post("/", response_model=PacienteResponse, status_code=status.HTTP_201_CREATED)
def crear_paciente(
    datos: PacienteCreate,
    current_user: Usuario = Depends(require_permission("PACIENTES_CREATE")),
    db: Session = Depends(get_db)
):
    # Validar documento duplicado
    existe = db.query(Paciente).filter(Paciente.numero_documento == datos.numero_documento).first()
    if existe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un paciente registrado con el documento {datos.numero_documento}"
        )

    # Crear paciente
    paciente_dict = datos.model_dump(exclude={"antecedentes"})
    nuevo_paciente = Paciente(**paciente_dict)
    db.add(nuevo_paciente)
    db.flush()

    # Crear ficha inicial de antecedentes
    ant_data = datos.antecedentes.model_dump() if datos.antecedentes else {}
    nuevo_antecedente = AntecedenteMedico(paciente_id=nuevo_paciente.id, **ant_data)
    db.add(nuevo_antecedente)

    # Log de auditoría
    log = AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="pacientes",
        registro_id=nuevo_paciente.id,
        accion=AuditoriaAccionEnum.INSERT,
        seccion_consultada="REGISTRO_PACIENTE",
        datos_nuevos={"numero_documento": nuevo_paciente.numero_documento, "nombre": f"{nuevo_paciente.nombres} {nuevo_paciente.apellidos}"}
    )
    db.add(log)
    db.commit()
    db.refresh(nuevo_paciente)
    return describir_uno(nuevo_paciente, db)

@router.get("/{id}", response_model=PacienteResponse)
def obtener_paciente(
    id: UUID,
    request: Request,
    current_user: Usuario = Depends(require_permission("PACIENTES_READ")),
    db: Session = Depends(get_db)
):
    paciente = db.query(Paciente).filter(Paciente.id == id).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    # Auditoría de visualización (VIEW)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    log = AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="pacientes",
        registro_id=paciente.id,
        accion=AuditoriaAccionEnum.VIEW,
        seccion_consultada="FICHA_DATOS_PERSONALES",
        ip_origen=client_ip,
        user_agent=user_agent
    )
    db.add(log)
    db.commit()

    return describir_uno(paciente, db)

@router.put("/{id}", response_model=PacienteResponse)
def actualizar_paciente(
    id: UUID,
    datos: PacienteUpdate,
    current_user: Usuario = Depends(require_permission("PACIENTES_UPDATE")),
    db: Session = Depends(get_db)
):
    paciente = db.query(Paciente).filter(Paciente.id == id).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    # Validar documento duplicado si se intenta cambiar
    if datos.numero_documento and datos.numero_documento != paciente.numero_documento:
        duplicado = db.query(Paciente).filter(Paciente.numero_documento == datos.numero_documento, Paciente.id != id).first()
        if duplicado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe otro paciente con el documento {datos.numero_documento}"
            )

    campos_actualizar = datos.model_dump(exclude_unset=True)
    # Reactivarlo a mano también le da de nuevo el plazo completo sin citas
    if campos_actualizar.get("estado") == EstadoRegistroEnum.ACTIVO:
        paciente.reactivado_en = datetime.now(timezone.utc)
    datos_previos = {}
    datos_nuevos = {}
    for field, value in campos_actualizar.items():
        val_anterior = getattr(paciente, field)
        datos_previos[field] = str(val_anterior) if val_anterior is not None else None
        setattr(paciente, field, value)
        datos_nuevos[field] = str(value) if value is not None else None

    # Auditoría
    log = AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="pacientes",
        registro_id=paciente.id,
        accion=AuditoriaAccionEnum.UPDATE,
        seccion_consultada="EDITAR_PACIENTE",
        datos_previos=datos_previos,
        datos_nuevos=datos_nuevos
    )
    db.add(log)
    db.commit()
    db.refresh(paciente)
    return describir_uno(paciente, db)

@router.get("/{id}/saldo")
def consultar_saldo_paciente(
    id: UUID,
    current_user: Usuario = Depends(require_permission("PACIENTES_READ")),
    db: Session = Depends(get_db)
):
    """
    Calcula en tiempo real el estado de cuenta y saldo pendiente del paciente.
    """
    paciente = db.query(Paciente).filter(Paciente.id == id).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    saldo = calcular_saldo_paciente(id, db)
    total_presupuestado = saldo.total_presupuestado
    total_pagado = saldo.total_pagado
    saldo_pendiente = float(saldo.pendiente)

    # Historial de pagos para la vista de cobranzas
    pagos_db = db.query(Pago).filter(Pago.paciente_id == id).order_by(Pago.fecha_hora.desc()).all()
    pagos_list = [
        {
            "id": str(p.id),
            "monto": float(p.monto),
            "medio_pago": p.metodo_pago.value if hasattr(p.metodo_pago, "value") else str(p.metodo_pago),
            "numero_comprobante": p.referencia_comprobante or f"REC-{str(p.id)[:8]}",
            "observaciones": p.observaciones,
            "es_cobro_directo": p.es_cobro_directo,
            "cobro_cita_id": str(p.cobro_cita_id) if p.cobro_cita_id else None,
            "anulado": p.anulado,
            "motivo_anulacion": p.motivo_anulacion,
            "fecha_anulacion": p.fecha_anulacion.isoformat() if p.fecha_anulacion else None,
            "created_at": p.fecha_hora.isoformat() if p.fecha_hora else None,
        }
        for p in pagos_db
    ]

    return {
        "paciente_id": str(paciente.id),
        "paciente": f"{paciente.nombres} {paciente.apellidos}",
        "total_presupuestado": float(total_presupuestado),
        "total_tratamientos": float(total_presupuestado),
        "total_pagado": float(total_pagado),
        "saldo_pendiente": saldo_pendiente,
        "estado_saldo": "DEUDOR" if saldo_pendiente > 0 else ("A_FAVOR" if saldo_pendiente < 0 else "AL_DIA"),
        "pagos": pagos_list
    }

@router.put("/{id}/antecedentes", response_model=AntecedenteMedicoResponse)
def actualizar_antecedentes(
    id: UUID,
    datos: AntecedenteMedicoUpdate,
    current_user: Usuario = Depends(require_permission("ANTECEDENTES_UPDATE")),
    db: Session = Depends(get_db)
):
    ant = db.query(AntecedenteMedico).filter(AntecedenteMedico.paciente_id == id).first()
    if not ant:
        ant = AntecedenteMedico(paciente_id=id)
        db.add(ant)

    for field, value in datos.model_dump(exclude_unset=True).items():
        setattr(ant, field, value)

    log = AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="antecedentes_medicos",
        registro_id=ant.id,
        accion=AuditoriaAccionEnum.UPDATE,
        seccion_consultada="ANTECEDENTES_MEDICOS"
    )
    db.add(log)
    db.commit()
    db.refresh(ant)
    return ant
