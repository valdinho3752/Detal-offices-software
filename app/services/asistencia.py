"""Reglas del turno: cada marcaje solo es válido según el marcaje anterior de la persona en el día."""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AsistenciaTipoEnum, RegistroAsistencia

ENTRADA = AsistenciaTipoEnum.ENTRADA
SALIDA = AsistenciaTipoEnum.SALIDA
INICIO_DESCANSO = AsistenciaTipoEnum.INICIO_DESCANSO
FIN_DESCANSO = AsistenciaTipoEnum.FIN_DESCANSO

SIGUIENTES = {
    None: (ENTRADA,),
    ENTRADA: (INICIO_DESCANSO, SALIDA),
    INICIO_DESCANSO: (FIN_DESCANSO,),
    FIN_DESCANSO: (INICIO_DESCANSO, SALIDA),
    SALIDA: (ENTRADA,),
}
ESTADOS = {
    None: "SIN_TURNO",
    ENTRADA: "EN_TURNO",
    INICIO_DESCANSO: "EN_DESCANSO",
    FIN_DESCANSO: "EN_TURNO",
    SALIDA: "TURNO_CERRADO",
}
MOTIVOS = {
    "SIN_TURNO": "Todavía no marcaste tu entrada de hoy",
    "EN_TURNO": "Ya tienes un turno abierto",
    "EN_DESCANSO": "Estás en descanso: primero marca el fin del descanso",
    "TURNO_CERRADO": "Tu turno ya está cerrado: marca una nueva entrada para volver a empezar",
}


@dataclass(frozen=True)
class EstadoTurno:
    estado: str
    permitidos: Tuple[AsistenciaTipoEnum, ...]
    desde: Optional[datetime]
    # Una jornada anterior sin salida no impide trabajar hoy, pero debe corregirse
    jornada_sin_salida: Optional[date]

    @property
    def motivo_bloqueo(self) -> str:
        return MOTIVOS[self.estado]


def consultar_estado(usuario_id: UUID, db: Session) -> EstadoTurno:
    ultimo = (
        db.query(RegistroAsistencia)
        .filter(RegistroAsistencia.usuario_id == usuario_id)
        .order_by(RegistroAsistencia.fecha_hora.desc())
        .first()
    )
    hoy = db.query(func.current_date()).scalar()
    if ultimo is None or ultimo.fecha_hora.date() < hoy:
        sin_salida = ultimo.fecha_hora.date() if ultimo and ultimo.tipo_evento != SALIDA else None
        return EstadoTurno(ESTADOS[None], SIGUIENTES[None], None, sin_salida)
    return EstadoTurno(ESTADOS[ultimo.tipo_evento], SIGUIENTES[ultimo.tipo_evento], ultimo.fecha_hora, None)
