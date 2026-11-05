from typing import Optional
from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, field_validator
from app.schemas.validaciones import validar_pieza_fdi, validar_url_imagen
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
    _validar_pieza = field_validator("pieza_fdi")(validar_pieza_fdi)
    _validar_url = field_validator("archivo_url")(validar_url_imagen)

class RadiografiaUpdate(BaseModel):
    _validar_pieza = field_validator("pieza_fdi")(validar_pieza_fdi)
    _validar_url = field_validator("archivo_url")(validar_url_imagen)

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
