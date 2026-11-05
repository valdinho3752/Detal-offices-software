from pydantic import BaseModel, ConfigDict, Field, field_validator

class ConfiguracionRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    moneda_simbolo: str

class ConfiguracionActualizar(BaseModel):
    moneda_simbolo: str = Field(max_length=8)

    @field_validator("moneda_simbolo")
    @classmethod
    def validar_simbolo(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("Indica el símbolo de la moneda")
        if any(c.isdigit() for c in valor):
            raise ValueError("El símbolo de la moneda no puede tener números")
        return valor
