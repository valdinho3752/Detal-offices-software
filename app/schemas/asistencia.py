from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.models.enums import AsistenciaTipoEnum

class AsistenciaCreate(BaseModel):
    tipo_evento: AsistenciaTipoEnum
    observaciones: Optional[str] = None

class AsistenciaResponse(BaseModel):
    id: UUID
    usuario_id: UUID
    tipo_evento: AsistenciaTipoEnum
    fecha_hora: datetime
    observaciones: Optional[str] = None
    ip_registro: Optional[str] = None

    class Config:
        from_attributes = True
