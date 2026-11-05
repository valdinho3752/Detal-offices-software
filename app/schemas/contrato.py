from typing import Optional
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel
from app.models.enums import TipoRemuneracionEnum

class ContratoRemuneracionBase(BaseModel):
    usuario_id: UUID
    tipo_remuneracion: Optional[TipoRemuneracionEnum] = TipoRemuneracionEnum.SUELDO_FIJO_MENSUAL
    salario_base: Decimal = Decimal("0.00")
    porcentaje_comision: Decimal = Decimal("0.00")
    valor_hora: Decimal = Decimal("0.00")
    fecha_inicio_contrato: Optional[date] = None
    activo: Optional[bool] = True

class ContratoRemuneracionCreate(ContratoRemuneracionBase):
    pass

class ContratoRemuneracionUpdate(BaseModel):
    tipo_remuneracion: Optional[TipoRemuneracionEnum] = None
    salario_base: Optional[Decimal] = None
    porcentaje_comision: Optional[Decimal] = None
    valor_hora: Optional[Decimal] = None
    activo: Optional[bool] = None

class ContratoRemuneracionResponse(ContratoRemuneracionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
