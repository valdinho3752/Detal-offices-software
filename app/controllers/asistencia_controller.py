from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AuditoriaAccionEnum, AuditoriaLog, RegistroAsistencia, ContratoRemuneracion, Usuario, RolCodigoEnum
from app.core.dependencies import get_current_user, require_permission, require_role, tiene_permiso
from app.schemas.asistencia import AsistenciaResponse, CorreccionMarcajeCreate, JornadaSinSalidaResponse
from app.services.asistencia import jornadas_sin_salida, validar_correccion
from app.schemas.contrato import (
    ContratoRemuneracionCreate, ContratoRemuneracionUpdate, ContratoRemuneracionResponse
)

router = APIRouter(prefix="/personal", tags=["Asistencia y Contratos Salariales"])

# ==================== ASISTENCIA ====================

@router.get("/asistencia", response_model=List[AsistenciaResponse])
def listar_asistencias(
    usuario_id: Optional[UUID] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(RegistroAsistencia)
    # Sin permiso de auditoría, cada empleado solo ve sus propios fichajes
    if not tiene_permiso(current_user, "ASISTENCIA_READ_ALL", db):
        query = query.filter(RegistroAsistencia.usuario_id == current_user.id)
    elif usuario_id:
        query = query.filter(RegistroAsistencia.usuario_id == usuario_id)

    if fecha_desde:
        query = query.filter(RegistroAsistencia.fecha_hora >= fecha_desde)
    if fecha_hasta:
        query = query.filter(RegistroAsistencia.fecha_hora <= fecha_hasta)

    return query.order_by(RegistroAsistencia.fecha_hora.desc()).all()

@router.get("/asistencia/jornadas-sin-salida", response_model=List[JornadaSinSalidaResponse])
def listar_jornadas_sin_salida(
    current_user: Usuario = Depends(require_role(RolCodigoEnum.ADMIN)),
    db: Session = Depends(get_db)
):
    return [
        JornadaSinSalidaResponse(
            usuario_id=registro.usuario_id,
            empleado_nombre=registro.empleado_nombre,
            empleado_rol=registro.empleado_rol,
            fecha=registro.fecha_hora.date(),
            ultimo_evento=registro.tipo_evento,
            ultima_hora=registro.fecha_hora,
        )
        for registro in jornadas_sin_salida(db)
    ]

@router.post("/asistencia/correcciones", response_model=AsistenciaResponse, status_code=status.HTTP_201_CREATED)
def corregir_marcaje(
    datos: CorreccionMarcajeCreate,
    current_user: Usuario = Depends(require_role(RolCodigoEnum.ADMIN)),
    db: Session = Depends(get_db)
):
    """Agrega un marcaje olvidado. Nunca modifica los existentes: queda identificado y con su motivo."""
    # El bloqueo evita que un marcaje simultáneo de la persona invalide la comprobación
    empleado = db.query(Usuario).filter(Usuario.id == datos.usuario_id).with_for_update(of=Usuario).first()
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    validar_correccion(datos.usuario_id, datos.tipo_evento, datos.fecha_hora, db)

    registro = RegistroAsistencia(
        usuario_id=datos.usuario_id,
        tipo_evento=datos.tipo_evento,
        fecha_hora=datos.fecha_hora,
        es_correccion=True,
        motivo_correccion=datos.motivo,
        corregido_por_usuario_id=current_user.id,
    )
    db.add(registro)
    db.flush()
    db.add(AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="registro_asistencia",
        registro_id=registro.id,
        accion=AuditoriaAccionEnum.INSERT,
        seccion_consultada="CORRECCION_MARCAJE",
        datos_nuevos={
            "empleado_id": str(datos.usuario_id),
            "tipo_evento": datos.tipo_evento.value,
            "fecha_hora": datos.fecha_hora.isoformat(),
            "motivo": datos.motivo,
        },
    ))
    db.commit()
    db.refresh(registro)
    return registro

# ==================== CONTRATOS SALARIALES ====================

@router.get("/contratos", response_model=List[ContratoRemuneracionResponse])
def listar_contratos(
    current_user: Usuario = Depends(require_permission("EMPLEADOS_READ")),
    db: Session = Depends(get_db)
):
    return db.query(ContratoRemuneracion).all()

@router.post("/contratos", response_model=ContratoRemuneracionResponse, status_code=status.HTTP_201_CREATED)
def crear_contrato(
    datos: ContratoRemuneracionCreate,
    current_user: Usuario = Depends(require_role(RolCodigoEnum.ADMIN)),
    db: Session = Depends(get_db)
):
    existe = db.query(ContratoRemuneracion).filter(ContratoRemuneracion.usuario_id == datos.usuario_id).first()
    if existe:
        raise HTTPException(status_code=400, detail="Este usuario ya cuenta con un contrato salarial asignado")
    contrato = ContratoRemuneracion(**datos.model_dump())
    db.add(contrato)
    db.commit()
    db.refresh(contrato)
    return contrato

@router.put("/contratos/{id}", response_model=ContratoRemuneracionResponse)
def actualizar_contrato(
    id: UUID,
    datos: ContratoRemuneracionUpdate,
    current_user: Usuario = Depends(require_role(RolCodigoEnum.ADMIN)),
    db: Session = Depends(get_db)
):
    contrato = db.query(ContratoRemuneracion).filter(ContratoRemuneracion.id == id).first()
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    for field, value in datos.model_dump(exclude_unset=True).items():
        setattr(contrato, field, value)
    db.commit()
    db.refresh(contrato)
    return contrato
