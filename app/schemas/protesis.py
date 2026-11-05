from typing import Optional, Any
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, model_validator
from app.models.enums import TipoTrabajoProtesisEnum, EstadoOrdenProtesisEnum

class OrdenLaboratorioCreate(BaseModel):
    paciente_id: UUID
    doctor_id: UUID
    item_plan_id: Optional[UUID] = None
    laboratorio_nombre: str
    tipo_trabajo: TipoTrabajoProtesisEnum
    piezas_dentales: Optional[str] = None
    color_guia_vita: Optional[str] = None
    instrucciones_tecnicas: Optional[str] = None
    costo_laboratorio: Decimal = Decimal("0.00")
    fecha_envio: Optional[date] = None
    fecha_entrega_esperada: Optional[date] = None
    observaciones: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def normalizar_campos(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalizar piezas_dentales / pieza_fdi
            if not data.get("piezas_dentales") and data.get("pieza_fdi") is not None:
                data["piezas_dentales"] = f"Pieza {data['pieza_fdi']}"
            elif not data.get("piezas_dentales"):
                data["piezas_dentales"] = "General"

            # Normalizar fecha_entrega_esperada / fecha_prometida_entrega
            if not data.get("fecha_entrega_esperada") and data.get("fecha_prometida_entrega"):
                data["fecha_entrega_esperada"] = data["fecha_prometida_entrega"]
            elif not data.get("fecha_entrega_esperada"):
                from datetime import timedelta
                data["fecha_entrega_esperada"] = date.today() + timedelta(days=7)

            # Normalizar color_guia_vita / color_vita
            if not data.get("color_guia_vita") and data.get("color_vita"):
                data["color_guia_vita"] = data["color_vita"]

            # Normalizar instrucciones_tecnicas / instrucciones
            if not data.get("instrucciones_tecnicas") and data.get("instrucciones"):
                data["instrucciones_tecnicas"] = data["instrucciones"]

        return data

class OrdenLaboratorioUpdate(BaseModel):
    doctor_id: Optional[UUID] = None
    laboratorio_nombre: Optional[str] = None
    piezas_dentales: Optional[str] = None
    color_guia_vita: Optional[str] = None
    instrucciones_tecnicas: Optional[str] = None
    costo_laboratorio: Optional[Decimal] = None
    fecha_entrega_esperada: Optional[date] = None
    fecha_recepcion_real: Optional[date] = None
    estado: Optional[EstadoOrdenProtesisEnum] = None
    egreso_caja_id: Optional[UUID] = None
    observaciones: Optional[str] = None

class OrdenLaboratorioResponse(OrdenLaboratorioCreate):
    id: UUID
    egreso_caja_id: Optional[UUID] = None
    fecha_recepcion_real: Optional[date] = None
    estado: EstadoOrdenProtesisEnum
    created_at: datetime

    class Config:
        from_attributes = True
