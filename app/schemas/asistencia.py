from typing import Annotated, List, Optional
from uuid import UUID
from datetime import date, datetime
from pydantic import AwareDatetime, BaseModel, Field, StringConstraints, field_validator, model_validator
from app.models.enums import AsistenciaTipoEnum

class AsistenciaCreate(BaseModel):
    tipo_evento: AsistenciaTipoEnum
    observaciones: Optional[str] = None

class AsistenciaResponse(BaseModel):
    id: UUID
    usuario_id: UUID
    tipo_evento: AsistenciaTipoEnum
    fecha_hora: datetime
    observaciones: Optional[str] = None
    ip_registro: Optional[str] = None
    empleado_nombre: Optional[str] = None
    empleado_rol: Optional[str] = None
    es_correccion: bool = False
    motivo_correccion: Optional[str] = None
    corregido_por_nombre: Optional[str] = None
    anulado: bool = False
    motivo_anulacion: Optional[str] = None
    anulado_por_nombre: Optional[str] = None

    class Config:
        from_attributes = True

class CorreccionMarcajeCreate(BaseModel):
    usuario_id: UUID
    tipo_evento: AsistenciaTipoEnum
    fecha_hora: AwareDatetime  # Con zona horaria: sin ella, la hora real sería ambigua
    motivo: str = Field(max_length=500)
    fecha_hora_fin: Optional[AwareDatetime] = None  # Solo para agregar un descanso completo

    @model_validator(mode="after")
    def validar_descanso(self):
        if self.fecha_hora_fin is None:
            return self
        if self.tipo_evento != AsistenciaTipoEnum.INICIO_DESCANSO:
            raise ValueError("Solo un descanso puede tener hora de fin")
        if self.fecha_hora_fin <= self.fecha_hora:
            raise ValueError("El fin del descanso debe ser posterior a su inicio")
        return self

    @field_validator("motivo")
    @classmethod
    def validar_motivo(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("Indica el motivo de la corrección")
        return valor

class AnulacionMarcaje(BaseModel):
    motivo: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]

class JornadaSinSalidaResponse(BaseModel):
    usuario_id: UUID
    empleado_nombre: str
    empleado_rol: Optional[str] = None
    fecha: date
    ultimo_evento: AsistenciaTipoEnum
    ultima_hora: datetime

class EstadoTurnoResponse(BaseModel):
    estado: str
    permitidos: List[AsistenciaTipoEnum]
    desde: Optional[datetime] = None
    jornada_sin_salida: Optional[date] = None
