from typing import Optional
from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel
from app.models.enums import TipoEstudioImagenEnum

class RadiografiaBase(BaseModel):
    paciente_id: UUID
    visita_id: Optional[UUID] = None
    pieza_fdi: Optional[int] = None
    tipo_estudio: TipoEstudioImagenEnum
    titulo: str
    archivo_url: str
    mime_type: Optional[str] = "image/jpeg"
    tamano_bytes: Optional[int] = None
    informe_diagnostico: Optional[str] = None
    fecha_toma: Optional[date] = None

class RadiografiaCreate(RadiografiaBase):
    pass

class RadiografiaUpdate(BaseModel):
    pieza_fdi: Optional[int] = None
    tipo_estudio: Optional[TipoEstudioImagenEnum] = None
    titulo: Optional[str] = None
    archivo_url: Optional[str] = None
    informe_diagnostico: Optional[str] = None
    fecha_toma: Optional[date] = None

class RadiografiaResponse(RadiografiaBase):
    id: UUID
    subido_por_usuario_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
