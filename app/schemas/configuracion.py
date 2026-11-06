from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

TemaClinica = Literal["claro", "oscuro"]

class ConfiguracionPublica(BaseModel):
    """Lo que se necesita antes de iniciar sesión, para mostrar la pantalla de acceso."""
    nombre_clinica: str
    tema_por_defecto: TemaClinica
    logo_url: Optional[str] = None
    zona_horaria: Optional[str] = None

class ConfiguracionRespuesta(ConfiguracionPublica):
    moneda_simbolo: str

class ConfiguracionActualizar(BaseModel):
    moneda_simbolo: Optional[str] = Field(default=None, max_length=8)
    nombre_clinica: Optional[str] = Field(default=None, max_length=120)
    tema_por_defecto: Optional[TemaClinica] = None

    @field_validator("moneda_simbolo")
    @classmethod
    def validar_simbolo(cls, valor):
        if valor is None:
            raise ValueError("Indica el símbolo de la moneda")
        valor = valor.strip()
        if not valor:
            raise ValueError("Indica el símbolo de la moneda")
        if any(c.isdigit() for c in valor):
            raise ValueError("El símbolo de la moneda no puede tener números")
        return valor

    @field_validator("nombre_clinica")
    @classmethod
    def validar_nombre(cls, valor):
        if valor is None or not valor.strip():
            raise ValueError("Indica el nombre de la clínica")
        return valor.strip()

    @field_validator("tema_por_defecto")
    @classmethod
    def validar_tema(cls, valor):
        if valor is None:
            raise ValueError("Elige el tema por defecto")
        return valor
