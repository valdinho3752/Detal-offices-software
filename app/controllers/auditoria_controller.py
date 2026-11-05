from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AuditoriaLog, Usuario, RolCodigoEnum, AuditoriaAccionEnum
from app.core.dependencies import require_permission
from app.schemas.auditoria import AuditoriaLogResponse

router = APIRouter(prefix="/auditoria", tags=["Auditoría de Acciones y Vistas (Logs)"])

@router.get("/", response_model=List[AuditoriaLogResponse])
def consultar_auditoria(
    usuario_id: Optional[UUID] = None,
    tabla_afectada: Optional[str] = None,
    accion: Optional[AuditoriaAccionEnum] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    limit: int = 100,
    current_user: Usuario = Depends(require_permission("AUDITORIA_READ")),
    db: Session = Depends(get_db)
):
    query = db.query(AuditoriaLog)
    if usuario_id:
        query = query.filter(AuditoriaLog.usuario_id == usuario_id)
    if tabla_afectada:
        query = query.filter(AuditoriaLog.tabla_afectada == tabla_afectada)
    if accion:
        query = query.filter(AuditoriaLog.accion == accion)
    if fecha_desde:
        query = query.filter(AuditoriaLog.fecha_hora >= fecha_desde)
    if fecha_hasta:
        query = query.filter(AuditoriaLog.fecha_hora <= fecha_hasta)

    return query.order_by(AuditoriaLog.fecha_hora.desc()).limit(limit).all()
