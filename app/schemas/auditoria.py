from typing import Optional, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.models.enums import AuditoriaAccionEnum

class AuditoriaLogResponse(BaseModel):
    id: UUID
    usuario_id: Optional[UUID] = None
    usuario_nombre: Optional[str] = None
    tabla_afectada: str
    registro_id: Optional[UUID] = None
    accion: AuditoriaAccionEnum
    seccion_consultada: Optional[str] = None
    datos_previos: Optional[Any] = None
    datos_nuevos: Optional[Any] = None
    ip_origen: Optional[str] = None
    user_agent: Optional[str] = None
    fecha_hora: datetime

    class Config:
        from_attributes = True
