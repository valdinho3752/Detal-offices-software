from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel
from app.models.enums import EstadoCajaEnum, MetodoPagoEnum, CategoriaEgresoCajaEnum

class CajaAperturaRequest(BaseModel):
    monto_inicial_fondo: Optional[Decimal] = Decimal("0.00")
    monto_apertura: Optional[Decimal] = None
    observaciones: Optional[str] = None

class CajaCierreRequest(BaseModel):
    total_efectivo_contado: Optional[Decimal] = None
    monto_cierre_real: Optional[Decimal] = None
    observaciones: Optional[str] = None

class CajaSesionResponse(BaseModel):
    id: UUID
    usuario_apertura_id: UUID
    usuario_cierre_id: Optional[UUID] = None
    fecha_apertura: datetime
    fecha_cierre: Optional[datetime] = None
    monto_inicial_fondo: Decimal
    total_ingresos_efectivo: Decimal
    total_egresos_efectivo: Decimal
    saldo_efectivo_esperado: Decimal
    total_efectivo_contado: Optional[Decimal] = None
    diferencia_descuadre: Optional[Decimal] = None
    estado: EstadoCajaEnum
    observaciones: Optional[str] = None

    class Config:
        from_attributes = True

class PagoCreate(BaseModel):
    paciente_id: UUID
    plan_id: Optional[UUID] = None
    visita_id: Optional[UUID] = None
    doctor_comision_id: Optional[UUID] = None
    monto: Decimal
    metodo_pago: MetodoPagoEnum = MetodoPagoEnum.EFECTIVO
    referencia_comprobante: Optional[str] = None
    observaciones: Optional[str] = None

class PagoResponse(PagoCreate):
    id: UUID
    caja_sesion_id: Optional[UUID] = None
    registrado_por_usuario_id: UUID
    fecha_hora: datetime

    class Config:
        from_attributes = True

class EgresoCajaCreate(BaseModel):
    categoria: CategoriaEgresoCajaEnum
    monto: Decimal
    concepto_motivo: str
    numero_recibo_comprobante: Optional[str] = None
    usuario_beneficiario_id: Optional[UUID] = None

class EgresoCajaResponse(EgresoCajaCreate):
    id: UUID
    caja_sesion_id: UUID
    usuario_autoriza_id: UUID
    fecha_hora: datetime

    class Config:
        from_attributes = True
