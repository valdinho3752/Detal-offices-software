from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import TipoPagoEmpleadoEnum

class PagoEmpleadoCreate(BaseModel):
    # Rechaza campos desconocidos: un nombre mal escrito no debe perderse en silencio
    model_config = ConfigDict(extra="forbid")

    usuario_empleado_id: UUID
    caja_sesion_id: Optional[UUID] = None
    tipo_pago: TipoPagoEmpleadoEnum
    monto_base: Decimal = Field(default=Decimal("0.00"), ge=0)
    monto_comisiones: Decimal = Field(default=Decimal("0.00"), ge=0)
    deducciones_descuentos: Decimal = Field(default=Decimal("0.00"), ge=0)
    monto_neto_pagado: Decimal = Field(gt=0)
    metodo_pago: str = "EFECTIVO_CAJA"
    referencia_pago: Optional[str] = None
    observaciones: Optional[str] = None

class PagoEmpleadoResponse(PagoEmpleadoCreate):
    # Las respuestas no vuelven a validar montos: deben poder mostrar registros antiguos
    monto_base: Optional[Decimal] = None
    monto_comisiones: Optional[Decimal] = None
    deducciones_descuentos: Optional[Decimal] = None
    monto_neto_pagado: Decimal
    id: UUID
    usuario_autoriza_id: UUID
    fecha_hora_pago: datetime

    class Config:
        from_attributes = True
