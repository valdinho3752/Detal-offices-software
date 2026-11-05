from typing import Optional
from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, EmailStr, field_validator
from app.models.enums import GeneroEnum, EstadoRegistroEnum

def _no_futura(valor):
    if valor and valor > date.today():
        raise ValueError("La fecha de nacimiento no puede ser futura")
    return valor

class AntecedenteMedicoUpdate(BaseModel):
    enfermedades_sistemicas: Optional[str] = None
    alergias: Optional[str] = None
    medicamentos_actuales: Optional[str] = None
    cirugias_previas: Optional[str] = None
    fuma: Optional[bool] = False
    embarazada: Optional[bool] = False
    observaciones: Optional[str] = None

class AntecedenteMedicoResponse(BaseModel):
    id: UUID
    paciente_id: UUID
    enfermedades_sistemicas: Optional[str] = None
    alergias: Optional[str] = None
    medicamentos_actuales: Optional[str] = None
    cirugias_previas: Optional[str] = None
    fuma: bool
    embarazada: bool
    observaciones: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True

class PacienteBase(BaseModel):
    nombres: str
    apellidos: str
    tipo_documento: str = "DNI"
    numero_documento: str
    fecha_nacimiento: date
    genero: Optional[GeneroEnum] = GeneroEnum.OTRO
    telefono: str
    email: Optional[EmailStr] = None
    direccion: Optional[str] = None
    ocupacion: Optional[str] = None
    contacto_emergencia_nombre: Optional[str] = None
    contacto_emergencia_telefono: Optional[str] = None
    estado: Optional[EstadoRegistroEnum] = EstadoRegistroEnum.ACTIVO

class PacienteCreate(PacienteBase):
    _validar_nacimiento = field_validator("fecha_nacimiento")(_no_futura)

    antecedentes: Optional[AntecedenteMedicoUpdate] = None

class PacienteUpdate(BaseModel):
    _validar_nacimiento = field_validator("fecha_nacimiento")(_no_futura)

    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    tipo_documento: Optional[str] = None
    numero_documento: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    genero: Optional[GeneroEnum] = None
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    direccion: Optional[str] = None
    ocupacion: Optional[str] = None
    contacto_emergencia_nombre: Optional[str] = None
    contacto_emergencia_telefono: Optional[str] = None
    estado: Optional[EstadoRegistroEnum] = None

class PacienteResponse(PacienteBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    antecedentes: Optional[AntecedenteMedicoResponse] = None

    class Config:
        from_attributes = True
