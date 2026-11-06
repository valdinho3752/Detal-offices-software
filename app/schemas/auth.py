from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from app.core.contrasenas import validar_contrasena
from app.models.enums import RolCodigoEnum

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class CambioContrasena(BaseModel):
    actual: str
    nueva: str

    @field_validator("nueva")
    @classmethod
    def validar_nueva(cls, valor: str) -> str:
        return validar_contrasena(valor)

class PreferenciaSesion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Más allá de 8 horas no hace falta: la sesión vence de todos modos
    minutos_inactividad: Literal[5, 10, 15, 30, 60, 120, 480]


class UsuarioSimpleResponse(BaseModel):
    id: UUID
    username: str
    nombre: str
    apellido: str
    email: EmailStr
    telefono: Optional[str] = None
    rol: str
    rol_nombre: Optional[str] = None
    activo: bool
    doctor_id: Optional[UUID] = None
    permisos: List[str] = []
    debe_cambiar_contrasena: bool = False
    minutos_inactividad: int = 5

    class Config:
        from_attributes = True
