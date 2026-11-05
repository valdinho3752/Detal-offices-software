from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.models.enums import RolCodigoEnum

class RolBase(BaseModel):
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    es_sistema: Optional[bool] = False

class RolCreate(RolBase):
    pass

class RolResponse(RolBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class PermisoResponse(BaseModel):
    id: UUID
    modulo: str
    accion: str
    codigo_permiso: str
    descripcion: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class DoctorBase(BaseModel):
    especialidad: str = "Odontología General"
    numero_colegiatura: Optional[str] = None
    color_agenda: Optional[str] = "#3B82F6"

class DoctorCreate(DoctorBase):
    usuario_id: UUID

class DoctorUpdate(BaseModel):
    especialidad: Optional[str] = None
    numero_colegiatura: Optional[str] = None
    color_agenda: Optional[str] = None

class DoctorResponse(DoctorBase):
    id: UUID
    usuario_id: UUID
    created_at: datetime
    usuario: Optional[UsuarioBase] = None

    class Config:
        from_attributes = True

class AsistenteBase(BaseModel):
    notas: Optional[str] = None

class AsistenteCreate(AsistenteBase):
    usuario_id: UUID

class AsistenteUpdate(BaseModel):
    notas: Optional[str] = None

class AsistenteResponse(AsistenteBase):
    id: UUID
    usuario_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class UsuarioBase(BaseModel):
    username: str
    nombre: str
    apellido: str
    email: EmailStr
    telefono: Optional[str] = None
    activo: Optional[bool] = True

class UsuarioCreate(UsuarioBase):
    password: str
    rol_id: UUID
    doctor_perfil: Optional[DoctorBase] = None
    asistente_perfil: Optional[AsistenteBase] = None

class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    activo: Optional[bool] = None
    rol_id: Optional[UUID] = None
    password: Optional[str] = None
    doctor_perfil: Optional[DoctorUpdate] = None
    asistente_perfil: Optional[AsistenteUpdate] = None

class UsuarioDetailResponse(UsuarioBase):
    id: UUID
    rol_id: UUID
    rol: Optional[RolResponse] = None
    doctor_perfil: Optional[DoctorResponse] = None
    asistente_perfil: Optional[AsistenteResponse] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
