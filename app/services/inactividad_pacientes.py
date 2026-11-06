"""
Un paciente está inactivo si se marcó a mano, o si lleva el plazo configurado sin citas.
Lo segundo se calcula al consultar: siempre está al día y no depende de una tarea programada.
"""
import calendar
from datetime import datetime, timezone
from typing import Iterable, Optional

from sqlalchemy import func, not_, or_
from sqlalchemy.orm import Session

from app.models import Cita, EstadoCitaEnum, Paciente
from app.models.enums import EstadoRegistroEnum
from app.services.moneda import obtener_configuracion

MOTIVO_MANUAL = "MANUAL"
MOTIVO_SIN_CITAS = "SIN_CITAS"
# Una cita cancelada o a la que no llegó no demuestra que siga viniendo
_NO_CUENTAN = (EstadoCitaEnum.CANCELADA, EstadoCitaEnum.NO_ASISTIO)


def _hace_meses(meses: int, ahora: datetime) -> datetime:
    total = ahora.year * 12 + ahora.month - 1 - meses
    anio, mes = total // 12, total % 12 + 1
    return ahora.replace(year=anio, month=mes, day=min(ahora.day, calendar.monthrange(anio, mes)[1]))


def _limite(db: Session) -> Optional[datetime]:
    meses = obtener_configuracion(db).meses_inactividad_paciente
    return _hace_meses(meses, datetime.now(timezone.utc)) if meses > 0 else None


def _subconsulta_ultima_cita(db: Session):
    return (
        db.query(Cita.paciente_id.label("paciente_id"), func.max(Cita.fecha_inicio_programada).label("ultima"))
        .filter(Cita.estado.notin_(_NO_CUENTAN))
        .group_by(Cita.paciente_id)
        .subquery()
    )


def consulta_con_ultima_cita(db: Session):
    ultima = _subconsulta_ultima_cita(db)
    return db.query(Paciente, ultima.c.ultima).outerjoin(ultima, ultima.c.paciente_id == Paciente.id), ultima


def filtro_inactivos(ultima, db: Session):
    limite = _limite(db)
    manual = Paciente.estado == EstadoRegistroEnum.INACTIVO
    if not limite:
        return manual
    referencia = func.greatest(Paciente.created_at, ultima.c.ultima, Paciente.reactivado_en)
    return or_(manual, referencia < limite)


def filtro_activos(ultima, db: Session):
    return not_(filtro_inactivos(ultima, db))


def describir(paciente: Paciente, ultima_cita: Optional[datetime], limite: Optional[datetime]) -> Paciente:
    """Añade al paciente los datos de su situación, que la respuesta de la API incluye."""
    referencias = [f for f in (paciente.created_at, ultima_cita, paciente.reactivado_en) if f]
    motivo = None
    if paciente.estado == EstadoRegistroEnum.INACTIVO:
        motivo = MOTIVO_MANUAL
    elif limite and referencias and max(referencias) < limite:
        motivo = MOTIVO_SIN_CITAS
    paciente.ultima_cita = ultima_cita
    paciente.inactivo = motivo is not None
    paciente.motivo_inactividad = motivo
    return paciente


def describir_filas(filas: Iterable, db: Session) -> list:
    limite = _limite(db)
    return [describir(paciente, ultima, limite) for paciente, ultima in filas]


def describir_uno(paciente: Paciente, db: Session) -> Paciente:
    ultima = (
        db.query(func.max(Cita.fecha_inicio_programada))
        .filter(Cita.paciente_id == paciente.id, Cita.estado.notin_(_NO_CUENTAN))
        .scalar()
    )
    return describir(paciente, ultima, _limite(db))
