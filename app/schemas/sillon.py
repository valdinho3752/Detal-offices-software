from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, StringConstraints

Nombre = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Especialidad = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]


class SillonCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: Optional[Nombre] = None  # Sin nombre se usa "Box" y su número
    especialidad: Optional[Especialidad] = None


class SillonActualizar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: Optional[Nombre] = None
    especialidad: Optional[Especialidad] = None
    activo: Optional[bool] = None


class SillonRespuesta(BaseModel):
    id: UUID
    numero: int
    nombre: str
    especialidad: Optional[str] = None
    activo: bool
    created_at: datetime

    class Config:
        from_attributes = True
