from typing import Optional
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from app.models.enums import TipoRemuneracionEnum

class ContratoRemuneracionBase(BaseModel):
    usuario_id: UUID
    tipo_remuneracion: Optional[TipoRemuneracionEnum] = TipoRemuneracionEnum.SUELDO_FIJO_MENSUAL
    salario_base: Decimal = Field(default=Decimal("0.00"), ge=0)
    porcentaje_comision: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    valor_hora: Decimal = Field(default=Decimal("0.00"), ge=0)
    fecha_inicio_contrato: Optional[date] = None
    activo: Optional[bool] = True

class ContratoRemuneracionCreate(ContratoRemuneracionBase):
    pass

class ContratoRemuneracionUpdate(BaseModel):
    tipo_remuneracion: Optional[TipoRemuneracionEnum] = None
    salario_base: Optional[Decimal] = Field(default=None, ge=0)
    porcentaje_comision: Optional[Decimal] = Field(default=None, ge=0, le=100)
    valor_hora: Optional[Decimal] = Field(default=None, ge=0)
    activo: Optional[bool] = None

class ContratoRemuneracionResponse(BaseModel):
    usuario_id: UUID
    tipo_remuneracion: Optional[TipoRemuneracionEnum] = None
    salario_base: Decimal
    porcentaje_comision: Decimal
    valor_hora: Decimal
    fecha_inicio_contrato: Optional[date] = None
    activo: Optional[bool] = True
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
