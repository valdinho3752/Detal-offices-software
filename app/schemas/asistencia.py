from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
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
    empleado_nombre: Optional[str] = None
    empleado_rol: Optional[str] = None

    class Config:
        from_attributes = True

class EstadoTurnoResponse(BaseModel):
    estado: str
    permitidos: List[AsistenciaTipoEnum]
    desde: Optional[datetime] = None
    jornada_sin_salida: Optional[date] = None
