from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.dependencies import require_permission
from app.models import CobroCita, EstadoCobroCitaEnum, Usuario
from app.schemas.cobro_cita import CobroActualizar, CobroCerrar, CobroCitaRespuesta, CobroConfirmar
from app.services.cobros_cita import actualizar_lineas, cerrar_sin_pago, confirmar_pago, obtener_cobro_pendiente

router = APIRouter(prefix="/cobros-cita", tags=["Cobros de Citas"])


@router.get("/", response_model=List[CobroCitaRespuesta])
def listar_cobros(
    estado: Optional[EstadoCobroCitaEnum] = None,
    paciente_id: Optional[UUID] = None,
    current_user: Usuario = Depends(require_permission("CAJA_PAGOS")),
    db: Session = Depends(get_db)
):
    query = db.query(CobroCita)
    if estado:
        query = query.filter(CobroCita.estado == estado)
    if paciente_id:
        query = query.filter(CobroCita.paciente_id == paciente_id)
    return query.order_by(CobroCita.created_at.desc()).all()


@router.get("/{id}", response_model=CobroCitaRespuesta)
def obtener_cobro(
    id: UUID,
    current_user: Usuario = Depends(require_permission("CAJA_PAGOS")),
    db: Session = Depends(get_db)
):
    cobro = db.query(CobroCita).filter(CobroCita.id == id).first()
    if not cobro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cobro no encontrado")
    return cobro


@router.put("/{id}", response_model=CobroCitaRespuesta)
def actualizar_cobro(
    id: UUID,
    datos: CobroActualizar,
    current_user: Usuario = Depends(require_permission("CAJA_PAGOS")),
    db: Session = Depends(get_db)
):
    cobro = obtener_cobro_pendiente(id, db)
    actualizar_lineas(cobro, datos.lineas, current_user.id, db)
    db.commit()
    db.refresh(cobro)
    return cobro


@router.post("/{id}/confirmar", response_model=CobroCitaRespuesta)
def confirmar_cobro(
    id: UUID,
    datos: CobroConfirmar,
    current_user: Usuario = Depends(require_permission("CAJA_PAGOS")),
    db: Session = Depends(get_db)
):
    """Aplica los cambios y registra el pago en una sola operación: si algo falla, no se guarda nada."""
    cobro = obtener_cobro_pendiente(id, db)
    confirmar_pago(cobro, datos, current_user.id, db)
    db.commit()
    db.refresh(cobro)
    return cobro


@router.post("/{id}/cerrar-sin-pago", response_model=CobroCitaRespuesta)
def cerrar_cobro_sin_pago(
    id: UUID,
    datos: CobroCerrar,
    current_user: Usuario = Depends(require_permission("CAJA_PAGOS")),
    db: Session = Depends(get_db)
):
    """Para una cortesía o un tratamiento ya cubierto por abonos: queda el motivo y no se registra pago."""
    cobro = obtener_cobro_pendiente(id, db)
    cerrar_sin_pago(cobro, datos.motivo, current_user.id, db)
    db.commit()
    db.refresh(cobro)
    return cobro
