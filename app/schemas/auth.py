from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr
from app.models.enums import RolCodigoEnum

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class UsuarioSimpleResponse(BaseModel):
    id: UUID
    username: str
    nombre: str
    apellido: str
    email: EmailStr
    telefono: Optional[str] = None
    rol: str
    activo: bool
    doctor_id: Optional[UUID] = None

    class Config:
        from_attributes = True
