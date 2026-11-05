from typing import Annotated, Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from app.models.enums import EstadoCajaEnum, MetodoPagoEnum, CategoriaEgresoCajaEnum

class CajaAperturaRequest(BaseModel):
    monto_inicial_fondo: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    monto_apertura: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    observaciones: Optional[str] = None

class CajaCierreRequest(BaseModel):
    total_efectivo_contado: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    monto_cierre_real: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
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
    # Rechaza campos desconocidos: un método de pago mal nombrado no debe registrarse como efectivo
    model_config = ConfigDict(extra="forbid")

    paciente_id: UUID
    plan_id: Optional[UUID] = None
    visita_id: Optional[UUID] = None
    doctor_comision_id: Optional[UUID] = None
    monto: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    metodo_pago: MetodoPagoEnum = MetodoPagoEnum.EFECTIVO
    referencia_comprobante: Optional[str] = None
    es_cobro_directo: bool = False
    observaciones: Optional[str] = None

class PagoAnular(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]

class PagoResponse(PagoCreate):
    # Las respuestas no vuelven a validar montos: deben poder mostrar registros antiguos
    monto: Decimal
    id: UUID
    anulado: bool = False
    motivo_anulacion: Optional[str] = None
    fecha_anulacion: Optional[datetime] = None
    caja_sesion_id: Optional[UUID] = None
    registrado_por_usuario_id: UUID
    fecha_hora: datetime

    class Config:
        from_attributes = True

class EgresoCajaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categoria: CategoriaEgresoCajaEnum
    monto: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    concepto_motivo: str
    numero_recibo_comprobante: Optional[str] = None
    usuario_beneficiario_id: Optional[UUID] = None

class EgresoCajaResponse(EgresoCajaCreate):
    monto: Decimal
    id: UUID
    caja_sesion_id: UUID
    usuario_autoriza_id: UUID
    fecha_hora: datetime

    class Config:
        from_attributes = True
