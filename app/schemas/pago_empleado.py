from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.enums import TipoPagoEmpleadoEnum

TIPOS_SUELDO = (TipoPagoEmpleadoEnum.SUELDO_MENSUAL, TipoPagoEmpleadoEnum.QUINCENA)

class PagoEmpleadoBase(BaseModel):
    usuario_empleado_id: UUID
    caja_sesion_id: Optional[UUID] = None
    tipo_pago: TipoPagoEmpleadoEnum
    metodo_pago: str = "EFECTIVO_CAJA"
    referencia_pago: Optional[str] = None
    observaciones: Optional[str] = None

class PagoEmpleadoCreate(PagoEmpleadoBase):
    # Rechaza campos desconocidos: un nombre mal escrito no debe perderse en silencio
    model_config = ConfigDict(extra="forbid")

    monto_base: Decimal = Field(default=Decimal("0.00"), ge=0)
    monto_comisiones: Decimal = Field(default=Decimal("0.00"), ge=0)
    deducciones_descuentos: Decimal = Field(default=Decimal("0.00"), ge=0)
    monto_neto_pagado: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def validar_montos(self):
        es_sueldo = self.tipo_pago in TIPOS_SUELDO
        if self.deducciones_descuentos > 0 and not es_sueldo:
            raise ValueError("Solo un sueldo o quincena puede descontar adelantos")
        # Un sueldo cubierto por completo con adelantos no entrega dinero, pero sí debe registrarse
        if self.monto_neto_pagado == 0 and not (es_sueldo and self.deducciones_descuentos > 0):
            raise ValueError("El monto a pagar debe ser mayor a cero")
        if es_sueldo and self.monto_base > 0 and self.monto_base - self.deducciones_descuentos != self.monto_neto_pagado:
            raise ValueError("El monto a pagar debe ser el sueldo menos los adelantos descontados")
        return self

class PagoEmpleadoResponse(PagoEmpleadoBase):
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
