from typing import List, Optional, Dict
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel

class TratamientoDemandaItem(BaseModel):
    tratamiento_id: UUID
    codigo: str
    nombre: str
    categoria: str
    cantidad_realizada: int
    facturacion_total: Decimal

class ReporteTratamientosDemandaResponse(BaseModel):
    total_procedimientos_completados: int
    ranking_tratamientos: List[TratamientoDemandaItem]

class ProductividadDoctorItem(BaseModel):
    doctor_id: UUID
    doctor_nombre: str
    especialidad: str
    total_citas: int
    citas_finalizadas: int
    citas_no_asistio: int
    citas_canceladas: int
    tasa_ausentismo_porcentaje: float
    tiempo_total_sillon_minutos: int
    promedio_minutos_por_cita: float

class ReporteProductividadDoctoresResponse(BaseModel):
    resumen_global_citas: int
    doctores: List[ProductividadDoctorItem]

class ResumenFinancieroResponse(BaseModel):
    total_ingresos: Decimal
    ingresos_por_metodo: Dict[str, Decimal]
    total_egresos: Decimal
    egresos_por_categoria: Dict[str, Decimal]
    balance_neto_operativo: Decimal
