"""Reglas del turno: cada marcaje solo es válido según el marcaje anterior de la persona en el día."""
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import DateTime, func, literal, select
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


NOMBRES = {
    ENTRADA: "una entrada",
    SALIDA: "una salida",
    INICIO_DESCANSO: "un inicio de descanso",
    FIN_DESCANSO: "un fin de descanso",
}
MAXIMO_JORNADAS_PENDIENTES = 200


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
        .filter(RegistroAsistencia.usuario_id == usuario_id, RegistroAsistencia.anulado.is_(False))
        .order_by(RegistroAsistencia.fecha_hora.desc())
        .first()
    )
    hoy = db.query(func.current_date()).scalar()
    if ultimo is None or ultimo.fecha_hora.date() < hoy:
        sin_salida = ultimo.fecha_hora.date() if ultimo and ultimo.tipo_evento != SALIDA else None
        return EstadoTurno(ESTADOS[None], SIGUIENTES[None], None, sin_salida)
    return EstadoTurno(ESTADOS[ultimo.tipo_evento], SIGUIENTES[ultimo.tipo_evento], ultimo.fecha_hora, None)


def _marcajes_del_dia(usuario_id: UUID, fecha_hora: datetime, db: Session):
    dia = db.execute(select(func.date(literal(fecha_hora, DateTime(timezone=True))))).scalar()
    return db.query(RegistroAsistencia).filter(
        RegistroAsistencia.usuario_id == usuario_id,
        RegistroAsistencia.anulado.is_(False),
        func.date(RegistroAsistencia.fecha_hora) == dia,
    )


def validar_correccion(
    usuario_id: UUID, tipo: AsistenciaTipoEnum, fecha_hora: datetime, db: Session, fin_descanso: Optional[datetime] = None
) -> None:
    """
    Se comprueba contra los marcajes vecinos del mismo día: el resultado debe ser una jornada posible.
    Con fin_descanso se agrega el descanso completo, como un solo paso.
    """
    ultimo_momento = fin_descanso or fecha_hora
    if ultimo_momento > datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se puede registrar un marcaje en el futuro")

    del_dia = _marcajes_del_dia(usuario_id, fecha_hora, db)
    anterior = (
        del_dia.filter(RegistroAsistencia.fecha_hora <= fecha_hora)
        .order_by(RegistroAsistencia.fecha_hora.desc()).first()
    )
    siguiente = (
        del_dia.filter(RegistroAsistencia.fecha_hora > fecha_hora)
        .order_by(RegistroAsistencia.fecha_hora).first()
    )

    previo = anterior.tipo_evento if anterior else None
    if tipo not in SIGUIENTES[previo]:
        contexto = f"después de {NOMBRES[previo]}" if previo else "como primer marcaje del día"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"No puede haber {NOMBRES[tipo]} {contexto}")

    ultimo_tipo = tipo
    if fin_descanso:
        if siguiente and siguiente.fecha_hora <= fin_descanso:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"El descanso no puede abarcar {NOMBRES[siguiente.tipo_evento]}")
        ultimo_tipo = FIN_DESCANSO
    if siguiente and siguiente.tipo_evento not in SIGUIENTES[ultimo_tipo]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No puede haber {NOMBRES[ultimo_tipo]} antes de {NOMBRES[siguiente.tipo_evento]}",
        )


def validar_anulacion(registro: RegistroAsistencia, db: Session) -> None:
    """Sin este marcaje, la jornada debe seguir siendo posible."""
    if registro.anulado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este marcaje ya está anulado")
    del_dia = _marcajes_del_dia(registro.usuario_id, registro.fecha_hora, db).filter(RegistroAsistencia.id != registro.id)
    anterior = (
        del_dia.filter(RegistroAsistencia.fecha_hora <= registro.fecha_hora)
        .order_by(RegistroAsistencia.fecha_hora.desc()).first()
    )
    siguiente = (
        del_dia.filter(RegistroAsistencia.fecha_hora > registro.fecha_hora)
        .order_by(RegistroAsistencia.fecha_hora).first()
    )
    previo = anterior.tipo_evento if anterior else None
    if siguiente and siguiente.tipo_evento not in SIGUIENTES[previo]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede anular: quedaría {NOMBRES[siguiente.tipo_evento]} sin el marcaje que le corresponde antes. Anula primero los marcajes posteriores.",
        )


def jornadas_sin_salida(db: Session) -> List[RegistroAsistencia]:
    """Último marcaje de cada día anterior que no terminó en salida."""
    dia = func.date(RegistroAsistencia.fecha_hora)
    orden = func.row_number().over(
        partition_by=(RegistroAsistencia.usuario_id, dia),
        order_by=RegistroAsistencia.fecha_hora.desc(),
    ).label("orden")
    ultimos = select(RegistroAsistencia.id, orden).where(RegistroAsistencia.anulado.is_(False)).subquery()
    return (
        db.query(RegistroAsistencia)
        .join(ultimos, ultimos.c.id == RegistroAsistencia.id)
        .filter(
            ultimos.c.orden == 1,
            RegistroAsistencia.tipo_evento != SALIDA,
            dia < func.current_date(),
        )
        .order_by(RegistroAsistencia.fecha_hora.desc())
        .limit(MAXIMO_JORNADAS_PENDIENTES)
        .all()
    )
