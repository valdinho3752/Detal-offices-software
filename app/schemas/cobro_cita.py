from datetime import datetime
from decimal import Decimal
from typing import Annotated, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from app.models.enums import EstadoCobroCitaEnum, MetodoPagoEnum


class LineaCobroEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Optional[UUID] = None  # Sin id es una línea agregada a mano
    concepto: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
    monto: Decimal = Field(ge=0, decimal_places=2)


class CobroActualizar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lineas: List[LineaCobroEntrada] = Field(min_length=1)


class CobroConfirmar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lineas: Optional[List[LineaCobroEntrada]] = Field(default=None, min_length=1)
    metodo_pago: MetodoPagoEnum = MetodoPagoEnum.EFECTIVO
    referencia_comprobante: Optional[str] = None
    doctor_comision_id: Optional[UUID] = None
    observaciones: Optional[str] = None


class CobroCerrar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class LineaCobroRespuesta(BaseModel):
    id: UUID
    item_plan_id: Optional[UUID] = None
    concepto: str
    monto: Decimal
    costo_referencia: Optional[Decimal] = None
    aplica_a_plan: bool = False
    plan_titulo: Optional[str] = None

    class Config:
        from_attributes = True


class CobroCitaRespuesta(BaseModel):
    id: UUID
    cita_id: Optional[UUID] = None
    paciente_id: UUID
    paciente_nombre: Optional[str] = None
    doctor_id: UUID
    doctor_nombre: Optional[str] = None
    fecha_cita: Optional[datetime] = None
    motivo_cita: Optional[str] = None
    estado: EstadoCobroCitaEnum
    motivo_cierre: Optional[str] = None
    fecha_cierre: Optional[datetime] = None
    created_at: datetime
    total: Decimal
    lineas: List[LineaCobroRespuesta] = []

    class Config:
        from_attributes = True
