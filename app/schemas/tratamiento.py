from typing import Optional, List
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, model_validator
from app.models.enums import CategoriaTratamientoEnum, EstadoPlanEnum, EstadoItemPlanEnum

class CatalogoTratamientoBase(BaseModel):
    codigo: str
    categoria: CategoriaTratamientoEnum
    nombre: str
    descripcion: Optional[str] = None
    costo_base: Decimal = Decimal("0.00")
    duracion_estimada_min: int = 30
    activo: Optional[bool] = True

class CatalogoTratamientoCreate(CatalogoTratamientoBase):
    pass

class CatalogoTratamientoUpdate(BaseModel):
    codigo: Optional[str] = None
    categoria: Optional[CategoriaTratamientoEnum] = None
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    costo_base: Optional[Decimal] = None
    duracion_estimada_min: Optional[int] = None
    activo: Optional[bool] = None

class CatalogoTratamientoResponse(CatalogoTratamientoBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class ItemPlanTratamientoBase(BaseModel):
    tratamiento_id: Optional[UUID] = None
    catalogo_tratamiento_id: Optional[UUID] = None
    hallazgo_superficie_id: Optional[UUID] = None
    pieza_fdi: Optional[int] = None
    orden_secuencia: int = 1
    fecha_programada: Optional[date] = None
    estado: Optional[EstadoItemPlanEnum] = EstadoItemPlanEnum.PENDIENTE
    costo_acordado: Optional[Decimal] = None
    precio_unitario: Optional[Decimal] = None
    descuento: Optional[Decimal] = Decimal("0.00")
    superficie: Optional[str] = None
    es_proxima_sesion: Optional[bool] = False
    observaciones: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_costo_acordado(cls, data):
        if isinstance(data, dict):
            if not data.get("tratamiento_id") and data.get("catalogo_tratamiento_id"):
                data["tratamiento_id"] = data["catalogo_tratamiento_id"]
            if data.get("costo_acordado") is None:
                p_unit = Decimal(str(data.get("precio_unitario") or 0))
                desc = Decimal(str(data.get("descuento") or 0))
                data["costo_acordado"] = max(Decimal("0.00"), p_unit - desc)
            if data.get("es_proxima_sesion") and data.get("estado") in [EstadoItemPlanEnum.PENDIENTE, "PENDIENTE", None]:
                data["estado"] = EstadoItemPlanEnum.PROXIMA_SESION
        return data

class ItemPlanTratamientoCreate(ItemPlanTratamientoBase):
    plan_id: UUID

class ItemPlanTratamientoUpdate(BaseModel):
    tratamiento_id: Optional[UUID] = None
    hallazgo_superficie_id: Optional[UUID] = None
    pieza_fdi: Optional[int] = None
    orden_secuencia: Optional[int] = None
    fecha_programada: Optional[date] = None
    estado: Optional[EstadoItemPlanEnum] = None
    costo_acordado: Optional[Decimal] = None
    precio_unitario: Optional[Decimal] = None
    descuento: Optional[Decimal] = None
    superficie: Optional[str] = None
    es_proxima_sesion: Optional[bool] = None
    observaciones: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_update_fields(cls, data):
        if isinstance(data, dict):
            if data.get("es_proxima_sesion") is not None:
                if data["es_proxima_sesion"]:
                    data["estado"] = EstadoItemPlanEnum.PROXIMA_SESION
                elif data.get("estado") == EstadoItemPlanEnum.PROXIMA_SESION:
                    data["estado"] = EstadoItemPlanEnum.PENDIENTE
            if data.get("costo_acordado") is None and data.get("precio_unitario") is not None:
                p_unit = Decimal(str(data.get("precio_unitario") or 0))
                desc = Decimal(str(data.get("descuento") or 0))
                data["costo_acordado"] = max(Decimal("0.00"), p_unit - desc)
        return data

class ItemPlanTratamientoResponse(ItemPlanTratamientoBase):
    id: UUID
    plan_id: UUID
    created_at: datetime
    tratamiento: Optional[CatalogoTratamientoResponse] = None

    class Config:
        from_attributes = True

class PlanTratamientoBase(BaseModel):
    paciente_id: UUID
    doctor_id: Optional[UUID] = None
    titulo: Optional[str] = None
    nombre: Optional[str] = None
    estado: Optional[EstadoPlanEnum] = EstadoPlanEnum.PROPUESTO
    costo_total: Decimal = Decimal("0.00")
    fecha_creacion: Optional[date] = None

class PlanTratamientoCreate(PlanTratamientoBase):
    items: Optional[List[ItemPlanTratamientoBase]] = []

class PlanTratamientoUpdate(BaseModel):
    doctor_id: Optional[UUID] = None
    titulo: Optional[str] = None
    nombre: Optional[str] = None
    estado: Optional[EstadoPlanEnum] = None
    costo_total: Optional[Decimal] = None

class PlanTratamientoResponse(PlanTratamientoBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    items: List[ItemPlanTratamientoResponse] = []

    class Config:
        from_attributes = True
