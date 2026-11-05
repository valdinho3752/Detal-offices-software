from typing import Annotated, List, Optional
from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, StringConstraints

class VisitaEvolucionBase(BaseModel):
    paciente_id: UUID
    doctor_id: Optional[UUID] = None
    asistente_id: Optional[UUID] = None
    cita_id: Optional[UUID] = None
    item_plan_id: Optional[UUID] = None
    proximo_item_plan_id: Optional[UUID] = None
    fecha_hora: Optional[datetime] = None
    motivo_visita: Optional[str] = None
    motivo_consulta: Optional[str] = None
    diagnostico: str
    procedimiento_realizado: str
    receta_medicamentos: Optional[str] = None
    recomendaciones: Optional[str] = None
    observaciones_clinicas: Optional[str] = None
    fecha_proximo_control: Optional[date] = None
    indicaciones_proxima_visita: Optional[str] = None
    indicaciones_postoperatorias: Optional[str] = None

class VisitaEvolucionCreate(VisitaEvolucionBase):
    pass

class ObservacionEvolucionCreate(BaseModel):
    texto: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]

class ObservacionEvolucionResponse(BaseModel):
    id: UUID
    visita_id: UUID
    autor_usuario_id: Optional[UUID] = None
    autor_nombre: Optional[str] = None
    rol_autor: str
    texto: str
    created_at: datetime

    class Config:
        from_attributes = True

class VisitaEvolucionResponse(VisitaEvolucionBase):
    id: UUID
    fecha_hora: datetime
    created_at: datetime
    generada_automaticamente: bool = False
    doctor_nombre: Optional[str] = None
    observaciones: List[ObservacionEvolucionResponse] = []

    class Config:
        from_attributes = True
