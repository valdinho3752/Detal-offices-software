from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AuditoriaAccionEnum, AuditoriaLog, RegistroAsistencia, ContratoRemuneracion, Usuario, RolCodigoEnum
from app.core.dependencies import get_current_user, require_permission, require_role, tiene_permiso
from app.schemas.asistencia import AnulacionMarcaje, AsistenciaResponse, CorreccionMarcajeCreate, JornadaSinSalidaResponse
from app.services.asistencia import FIN_DESCANSO, jornadas_sin_salida, validar_anulacion, validar_correccion
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
    limit: int = Query(default=5000, ge=1, le=5000),
    skip: int = Query(default=0, ge=0),
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

    return query.order_by(RegistroAsistencia.fecha_hora.desc()).offset(skip).limit(limit).all()

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
    validar_correccion(datos.usuario_id, datos.tipo_evento, datos.fecha_hora, db, datos.fecha_hora_fin)

    registro = RegistroAsistencia(
        usuario_id=datos.usuario_id,
        tipo_evento=datos.tipo_evento,
        fecha_hora=datos.fecha_hora,
        es_correccion=True,
        motivo_correccion=datos.motivo,
        corregido_por_usuario_id=current_user.id,
    )
    db.add(registro)
    if datos.fecha_hora_fin:
        db.add(RegistroAsistencia(
            usuario_id=datos.usuario_id,
            tipo_evento=FIN_DESCANSO,
            fecha_hora=datos.fecha_hora_fin,
            es_correccion=True,
            motivo_correccion=datos.motivo,
            corregido_por_usuario_id=current_user.id,
        ))
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
            "fecha_hora_fin": datos.fecha_hora_fin.isoformat() if datos.fecha_hora_fin else None,
            "motivo": datos.motivo,
        },
    ))
    db.commit()
    db.refresh(registro)
    return registro

@router.post("/asistencia/{id}/anular", response_model=AsistenciaResponse)
def anular_marcaje(
    id: UUID,
    datos: AnulacionMarcaje,
    current_user: Usuario = Depends(require_role(RolCodigoEnum.ADMIN)),
    db: Session = Depends(get_db)
):
    """Un marcaje hecho por error deja de contar, pero sigue visible con su motivo."""
    registro = db.query(RegistroAsistencia).filter(RegistroAsistencia.id == id).first()
    if not registro:
        raise HTTPException(status_code=404, detail="Marcaje no encontrado")
    db.query(Usuario).filter(Usuario.id == registro.usuario_id).with_for_update(of=Usuario).first()
    validar_anulacion(registro, db)

    registro.anulado = True
    registro.motivo_anulacion = datos.motivo
    registro.anulado_por_usuario_id = current_user.id
    db.add(AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="registro_asistencia",
        registro_id=registro.id,
        accion=AuditoriaAccionEnum.UPDATE,
        seccion_consultada="ANULACION_MARCAJE",
        datos_previos={"anulado": False},
        datos_nuevos={"anulado": True, "motivo": datos.motivo},
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
