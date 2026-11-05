from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel
from app.models.enums import TipoPagoEmpleadoEnum

class PagoEmpleadoCreate(BaseModel):
    usuario_empleado_id: UUID
    caja_sesion_id: Optional[UUID] = None
    tipo_pago: TipoPagoEmpleadoEnum
    monto_base: Decimal = Decimal("0.00")
    monto_comisiones: Decimal = Decimal("0.00")
    deducciones_descuentos: Decimal = Decimal("0.00")
    monto_neto_pagado: Decimal
    metodo_pago: str = "EFECTIVO_CAJA"
    referencia_pago: Optional[str] = None
    observaciones: Optional[str] = None

class PagoEmpleadoResponse(PagoEmpleadoCreate):
    id: UUID
    usuario_autoriza_id: UUID
    fecha_hora_pago: datetime

    class Config:
        from_attributes = True
