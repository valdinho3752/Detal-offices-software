from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.models.enums import (
    TipoDenticionEnum, TipoOdontogramaEnum, EstadoDienteEnum,
    SuperficieDentalEnum, CondicionDentalEnum, EstadoClinicoHallazgoEnum
)

class HallazgoSuperficieBase(BaseModel):
    superficie: SuperficieDentalEnum
    condicion: CondicionDentalEnum
    estado_clinico: Optional[EstadoClinicoHallazgoEnum] = EstadoClinicoHallazgoEnum.REQUERIDO_PATOLOGIA
    color_hex: Optional[str] = "#EF4444"
    detalle: Optional[str] = None

class HallazgoSuperficieCreate(HallazgoSuperficieBase):
    pieza_dental_id: Optional[UUID] = None
    odontograma_id: Optional[UUID] = None
    pieza_fdi: Optional[int] = None

class HallazgoSuperficieUpdate(BaseModel):
    superficie: Optional[SuperficieDentalEnum] = None
    condicion: Optional[CondicionDentalEnum] = None
    estado_clinico: Optional[EstadoClinicoHallazgoEnum] = None
    color_hex: Optional[str] = None
    detalle: Optional[str] = None

class HallazgoSuperficieResponse(HallazgoSuperficieBase):
    id: UUID
    pieza_dental_id: UUID
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PiezaDentalBase(BaseModel):
    numero_fdi: int
    estado_general: Optional[EstadoDienteEnum] = EstadoDienteEnum.PRESENTE
    tiene_endodoncia: Optional[bool] = False
    tiene_perno_poste: Optional[bool] = False
    notas_pieza: Optional[str] = None

class PiezaDentalCreate(PiezaDentalBase):
    odontograma_id: UUID

class PiezaDentalUpdate(BaseModel):
    estado_general: Optional[EstadoDienteEnum] = None
    tiene_endodoncia: Optional[bool] = None
    tiene_perno_poste: Optional[bool] = None
    notas_pieza: Optional[str] = None

class PiezaDentalResponse(PiezaDentalBase):
    id: UUID
    odontograma_id: UUID
    hallazgos: List[HallazgoSuperficieResponse] = []

    class Config:
        from_attributes = True

class OdontogramaBase(BaseModel):
    paciente_id: UUID
    doctor_id: Optional[UUID] = None
    tipo_denticion: Optional[TipoDenticionEnum] = TipoDenticionEnum.ADULTA_PERMANENTE
    tipo_registro: Optional[TipoOdontogramaEnum] = TipoOdontogramaEnum.INICIAL_INGRESO
    observaciones_generales: Optional[str] = None

class OdontogramaCreate(OdontogramaBase):
    pass

class OdontogramaUpdate(BaseModel):
    doctor_id: Optional[UUID] = None
    tipo_denticion: Optional[TipoDenticionEnum] = None
    tipo_registro: Optional[TipoOdontogramaEnum] = None
    observaciones_generales: Optional[str] = None

class OdontogramaResponse(OdontogramaBase):
    id: UUID
    doctor_id: UUID
    fecha_registro: datetime
    created_at: datetime
    piezas: List[PiezaDentalResponse] = []

    class Config:
        from_attributes = True
