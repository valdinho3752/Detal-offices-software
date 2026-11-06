from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, model_validator
from app.models.enums import EstadoCitaEnum, EstadoCobroCitaEnum
from app.schemas.tratamiento import CatalogoTratamientoResponse

class CitaBase(BaseModel):
    paciente_id: UUID
    doctor_id: UUID
    item_plan_id: Optional[UUID] = None
    tratamiento_id: Optional[UUID] = None
    fecha_inicio_programada: datetime
    fecha_fin_programada: datetime
    motivo_consulta: str
    notas_adicionales: Optional[str] = None

class CitaCreate(BaseModel):
    paciente_id: UUID
    doctor_id: Optional[UUID] = None
    item_plan_id: Optional[UUID] = None
    tratamiento_id: Optional[UUID] = None
    fecha_inicio_programada: Optional[datetime] = None
    fecha_fin_programada: Optional[datetime] = None
    motivo_consulta: Optional[str] = None
    notas_adicionales: Optional[str] = None
    
    # Campos auxiliares enviados por interfaces frontend
    fecha: Optional[str] = None
    hora_inicio: Optional[str] = None
    hora_fin: Optional[str] = None
    motivo: Optional[str] = None
    box_numero: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def assemble_cita_fields(cls, values: dict):
        if not isinstance(values, dict):
            return values

        # 1. Resolver fecha_inicio_programada
        if not values.get("fecha_inicio_programada"):
            fecha = values.get("fecha")
            hora_inicio = values.get("hora_inicio") or "09:00"
            if fecha:
                fecha = str(fecha).strip()
                hora_inicio = str(hora_inicio).strip()
                if len(hora_inicio) == 5:
                    hora_inicio = f"{hora_inicio}:00"
                values["fecha_inicio_programada"] = f"{fecha}T{hora_inicio}"

        # 2. Resolver fecha_fin_programada
        if not values.get("fecha_fin_programada"):
            fecha = values.get("fecha")
            hora_fin = values.get("hora_fin") or "10:00"
            if fecha:
                fecha = str(fecha).strip()
                hora_fin = str(hora_fin).strip()
                if len(hora_fin) == 5:
                    hora_fin = f"{hora_fin}:00"
                values["fecha_fin_programada"] = f"{fecha}T{hora_fin}"

        # 3. Resolver motivo_consulta
        motivo = values.get("motivo_consulta") or values.get("motivo")
        if not motivo or not str(motivo).strip():
            values["motivo_consulta"] = "Consulta Odontológica General"
        else:
            values["motivo_consulta"] = str(motivo).strip()

        # 4. Incluir box en notas_adicionales si se pasa box_numero
        box = values.get("box_numero")
        if box:
            notas = values.get("notas_adicionales") or ""
            if f"Box {box}" not in notas:
                values["notas_adicionales"] = f"{notas} (Box {box})".strip() if notas else f"Box {box}"

        return values

class CitaUpdate(BaseModel):
    paciente_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    item_plan_id: Optional[UUID] = None
    tratamiento_id: Optional[UUID] = None
    fecha_inicio_programada: Optional[datetime] = None
    fecha_fin_programada: Optional[datetime] = None
    motivo_consulta: Optional[str] = None
    notas_adicionales: Optional[str] = None
    estado: Optional[EstadoCitaEnum] = None

    # Campos auxiliares enviados por interfaces frontend
    fecha: Optional[str] = None
    hora_inicio: Optional[str] = None
    hora_fin: Optional[str] = None
    motivo: Optional[str] = None
    box_numero: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def assemble_cita_update_fields(cls, values: dict):
        if not isinstance(values, dict):
            return values

        fecha = values.get("fecha")
        if fecha:
            fecha = str(fecha).strip()
            hora_inicio = values.get("hora_inicio")
            if hora_inicio and not values.get("fecha_inicio_programada"):
                hora_inicio = str(hora_inicio).strip()
                if len(hora_inicio) == 5:
                    hora_inicio = f"{hora_inicio}:00"
                values["fecha_inicio_programada"] = f"{fecha}T{hora_inicio}"

            hora_fin = values.get("hora_fin")
            if hora_fin and not values.get("fecha_fin_programada"):
                hora_fin = str(hora_fin).strip()
                if len(hora_fin) == 5:
                    hora_fin = f"{hora_fin}:00"
                values["fecha_fin_programada"] = f"{fecha}T{hora_fin}"

        motivo = values.get("motivo_consulta") or values.get("motivo")
        if motivo is not None:
            values["motivo_consulta"] = str(motivo).strip()

        box = values.get("box_numero")
        if box:
            notas = values.get("notas_adicionales") or ""
            # Reemplazar Box previo si ya tenía
            import re
            cleaned_notas = re.sub(r'\(?Box \d+\)?', '', notas).strip()
            values["notas_adicionales"] = f"{cleaned_notas} (Box {box})".strip() if cleaned_notas else f"Box {box}"

        return values

class CitaSillonControl(BaseModel):
    """Para registrar cuando el paciente entra o sale del sillón dental"""
    hora_inicio_sillon: Optional[datetime] = None
    hora_fin_sillon: Optional[datetime] = None
    hora_llegada_recepcion: Optional[datetime] = None
    estado: Optional[EstadoCitaEnum] = None

class PacienteDeCita(BaseModel):
    id: UUID
    nombres: str
    apellidos: str

    class Config:
        from_attributes = True

class DoctorDeCita(BaseModel):
    id: UUID
    nombre_completo: Optional[str] = None

    class Config:
        from_attributes = True

class CitaResponse(CitaBase):
    id: UUID
    paciente: Optional[PacienteDeCita] = None
    doctor: Optional[DoctorDeCita] = None
    hora_llegada_recepcion: Optional[datetime] = None
    hora_inicio_sillon: Optional[datetime] = None
    hora_fin_sillon: Optional[datetime] = None
    duracion_sillon_minutos: Optional[int] = None
    estado: EstadoCitaEnum
    tratamiento: Optional[CatalogoTratamientoResponse] = None
    cobro_id: Optional[UUID] = None
    cobro_estado: Optional[EstadoCobroCitaEnum] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
