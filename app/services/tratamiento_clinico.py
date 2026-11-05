"""
Reglas clínicas que se aplican cuando un tratamiento del plan queda realizado.

El odontograma INICIAL_INGRESO es el diagnóstico de ingreso del paciente y no se
modifica: los tratamientos realizados se registran en un odontograma EVOLUCION_ACTUAL,
que se crea como copia del inicial la primera vez que hace falta.
"""
import re
import unicodedata
from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.auditoria import AuditoriaLog
from app.models.cita import Cita
from app.models.enums import (
    AuditoriaAccionEnum,
    CategoriaTratamientoEnum,
    CondicionDentalEnum,
    EstadoClinicoHallazgoEnum,
    EstadoDienteEnum,
    SuperficieDentalEnum,
    TipoOdontogramaEnum,
)
from app.models.odontograma import HallazgoSuperficie, Odontograma, PiezaDental
from app.models.tratamiento import CatalogoTratamiento, ItemPlanTratamiento
from app.models.visita import VisitaEvolucion

COLOR_REALIZADO = "#3B82F6"
COLOR_PENDIENTE = "#EF4444"


@dataclass(frozen=True)
class ResultadoClinico:
    """Cómo queda la pieza dental después de realizar un tratamiento."""
    condicion: Optional[CondicionDentalEnum] = None
    estado_pieza: Optional[EstadoDienteEnum] = None
    tiene_endodoncia: bool = False


def _sin_acentos(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normalizado if not unicodedata.combining(c)).lower()


def resultado_de_tratamiento(tratamiento: Optional[CatalogoTratamiento]) -> ResultadoClinico:
    """
    Deduce el resultado a partir de la categoría y el nombre del tratamiento.
    Si no corresponde a ninguna condición dental (ortodoncia, limpieza, etc.) no se
    asigna condición, para no dejar en la ficha un dato clínico que no ocurrió.
    """
    if not tratamiento:
        return ResultadoClinico()

    nombre = _sin_acentos(tratamiento.nombre)
    categoria = tratamiento.categoria

    if re.search(r"extraccion|exodoncia", nombre):
        return ResultadoClinico(estado_pieza=EstadoDienteEnum.EXTRAIDO)
    if categoria == CategoriaTratamientoEnum.IMPLANTOLOGIA or "implante" in nombre:
        return ResultadoClinico(estado_pieza=EstadoDienteEnum.IMPLANTE)
    if categoria == CategoriaTratamientoEnum.ENDODONCIA or re.search(r"endodoncia|conducto", nombre):
        return ResultadoClinico(condicion=CondicionDentalEnum.ENDODONCIA, tiene_endodoncia=True)
    if "corona" in nombre:
        return ResultadoClinico(
            condicion=CondicionDentalEnum.CORONA,
            estado_pieza=EstadoDienteEnum.CORONA_PROTESICA,
        )
    if "incrustacion" in nombre:
        return ResultadoClinico(condicion=CondicionDentalEnum.INCRUSTACION)
    if "sellante" in nombre:
        return ResultadoClinico(condicion=CondicionDentalEnum.SELLANTE)
    if "amalgama" in nombre:
        return ResultadoClinico(condicion=CondicionDentalEnum.OBTURACION_AMALGAMA)
    if categoria == CategoriaTratamientoEnum.RESTAURADORA or re.search(r"resina|obturacion|restauracion", nombre):
        return ResultadoClinico(condicion=CondicionDentalEnum.OBTURACION_RESINA)
    return ResultadoClinico()


def normalizar_superficie(superficie) -> SuperficieDentalEnum:
    if not superficie:
        return SuperficieDentalEnum.GENERAL
    valor = superficie.value if hasattr(superficie, "value") else str(superficie).upper().strip()
    if valor in ("OCLUSAL", "INCISAL", "OCLUSAL_INCISAL"):
        return SuperficieDentalEnum.OCLUSAL_INCISAL
    if valor in ("LINGUAL", "PALATINO", "PALATINA", "LINGUAL_PALATINO"):
        return SuperficieDentalEnum.LINGUAL_PALATINO
    if valor in ("VESTIBULAR", "MESIAL", "DISTAL", "RAIZ"):
        return SuperficieDentalEnum(valor)
    return SuperficieDentalEnum.GENERAL


def _superficies_coinciden(a: SuperficieDentalEnum, b: SuperficieDentalEnum) -> bool:
    return a == b or SuperficieDentalEnum.GENERAL in (a, b)


def clonar_odontograma_como_evolucion(origen: Odontograma, doctor_id: UUID, db: Session) -> Odontograma:
    """Copia piezas y hallazgos a un nuevo odontograma de evolución, sin tocar el original."""
    nuevo = Odontograma(
        paciente_id=origen.paciente_id,
        doctor_id=doctor_id,
        tipo_denticion=origen.tipo_denticion,
        tipo_registro=TipoOdontogramaEnum.EVOLUCION_ACTUAL,
        observaciones_generales="Evolución y Plan Clínico basado en Odontograma Inicial",
    )
    db.add(nuevo)
    db.flush()

    for pieza in origen.piezas:
        copia = PiezaDental(
            odontograma_id=nuevo.id,
            numero_fdi=pieza.numero_fdi,
            estado_general=pieza.estado_general,
            tiene_endodoncia=pieza.tiene_endodoncia,
            tiene_perno_poste=pieza.tiene_perno_poste,
            notas_pieza=pieza.notas_pieza,
        )
        db.add(copia)
        db.flush()
        for hallazgo in pieza.hallazgos:
            db.add(HallazgoSuperficie(
                pieza_dental_id=copia.id,
                superficie=hallazgo.superficie,
                condicion=hallazgo.condicion,
                estado_clinico=hallazgo.estado_clinico,
                color_hex=hallazgo.color_hex,
                detalle=hallazgo.detalle,
            ))
    db.flush()
    return nuevo


def _obtener_odontograma_evolucion(paciente_id: UUID, doctor_id: UUID, db: Session) -> Optional[Odontograma]:
    def ultimo(tipo: TipoOdontogramaEnum) -> Optional[Odontograma]:
        return (
            db.query(Odontograma)
            .filter(Odontograma.paciente_id == paciente_id, Odontograma.tipo_registro == tipo)
            .order_by(Odontograma.fecha_registro.desc())
            .first()
        )

    evolucion = ultimo(TipoOdontogramaEnum.EVOLUCION_ACTUAL)
    if evolucion:
        return evolucion
    inicial = ultimo(TipoOdontogramaEnum.INICIAL_INGRESO)
    return clonar_odontograma_como_evolucion(inicial, doctor_id, db) if inicial else None


def _texto_enum(valor) -> str:
    return (valor.value if hasattr(valor, "value") else str(valor)).replace("_", " ").capitalize()


def describir_diagnostico(paciente_id: UUID, item: ItemPlanTratamiento, db: Session) -> Optional[str]:
    """
    Describe la patología pendiente que atiende el ítem, según el odontograma vigente.
    Debe llamarse antes de registrar el tratamiento, que cambia esos hallazgos.
    Devuelve None si no hay ninguna: el diagnóstico no se inventa.
    """
    numero_fdi = item.pieza_fdi or (item.hallazgo.pieza.numero_fdi if item.hallazgo else None)
    if not numero_fdi:
        return None
    odontograma = (
        db.query(Odontograma)
        .filter(Odontograma.paciente_id == paciente_id)
        .order_by(Odontograma.fecha_registro.desc())
        .first()
    )
    if not odontograma:
        return None
    pieza = db.query(PiezaDental).filter_by(odontograma_id=odontograma.id, numero_fdi=numero_fdi).first()
    if not pieza:
        return None

    objetivo = normalizar_superficie(item.superficie)
    descripciones = [
        f"{_texto_enum(h.condicion)} en pieza {numero_fdi}"
        + ("" if h.superficie == SuperficieDentalEnum.GENERAL else f" ({_texto_enum(h.superficie)})")
        for h in pieza.hallazgos
        if h.estado_clinico == EstadoClinicoHallazgoEnum.REQUERIDO_PATOLOGIA
        and _superficies_coinciden(h.superficie, objetivo)
    ]
    return "; ".join(descripciones) or None


def crear_evolucion_de_cita(
    cita: Cita,
    items: List[ItemPlanTratamiento],
    diagnosticos: List[str],
    usuario_id: UUID,
    db: Session,
) -> Optional[VisitaEvolucion]:
    """
    Crea la evolución de una cita finalizada, con la fecha de la cita. No admite más
    cambios que agregar observaciones. Si el doctor ya registró una nota para esta
    cita, la conserva y no crea otra.
    """
    if db.query(VisitaEvolucion).filter(VisitaEvolucion.cita_id == cita.id).first():
        return None

    procedimientos = []
    for item in items:
        nombre = item.tratamiento.nombre if item.tratamiento else "Tratamiento"
        superficie = normalizar_superficie(item.superficie)
        detalle = f" - Pieza {item.pieza_fdi}" if item.pieza_fdi else ""
        if item.pieza_fdi and superficie != SuperficieDentalEnum.GENERAL:
            detalle += f" ({_texto_enum(superficie)})"
        procedimientos.append(f"{nombre}{detalle}")

    visita = VisitaEvolucion(
        paciente_id=cita.paciente_id,
        doctor_id=cita.doctor_id,
        cita_id=cita.id,
        item_plan_id=items[0].id if items else None,
        fecha_hora=cita.fecha_inicio_programada,
        motivo_visita=cita.motivo_consulta,
        diagnostico="; ".join(diagnosticos) or "Sin diagnóstico registrado en el odontograma",
        procedimiento_realizado="\n".join(procedimientos) or cita.motivo_consulta,
        generada_automaticamente=True,
    )
    db.add(visita)
    db.flush()
    db.add(AuditoriaLog(
        usuario_id=usuario_id,
        tabla_afectada="visitas_evolucion",
        registro_id=visita.id,
        accion=AuditoriaAccionEnum.INSERT,
        seccion_consultada="EVOLUCION_AUTOMATICA_CITA",
    ))
    return visita


def registrar_tratamiento_realizado(
    paciente_id: UUID, doctor_id: UUID, item: ItemPlanTratamiento, db: Session
) -> None:
    """Refleja en el odontograma de evolución un ítem del plan que ya se realizó."""
    numero_fdi = item.pieza_fdi or (item.hallazgo.pieza.numero_fdi if item.hallazgo else None)
    if not numero_fdi:
        return

    odontograma = _obtener_odontograma_evolucion(paciente_id, doctor_id, db)
    if not odontograma:
        return
    pieza = db.query(PiezaDental).filter_by(odontograma_id=odontograma.id, numero_fdi=numero_fdi).first()
    if not pieza:
        return

    resultado = resultado_de_tratamiento(item.tratamiento)
    nombre = item.tratamiento.nombre if item.tratamiento else "Tratamiento Realizado"
    detalle = f"Alta médica: {nombre}"

    if resultado.estado_pieza:
        pieza.estado_general = resultado.estado_pieza
    if resultado.tiene_endodoncia:
        pieza.tiene_endodoncia = True

    if resultado.estado_pieza == EstadoDienteEnum.EXTRAIDO:
        # La pieza ya no existe: no quedan patologías pendientes sobre ella.
        for hallazgo in pieza.hallazgos:
            if hallazgo.estado_clinico == EstadoClinicoHallazgoEnum.REQUERIDO_PATOLOGIA:
                db.delete(hallazgo)
        db.flush()
        db.expire(pieza, ["hallazgos"])
        return

    objetivo = normalizar_superficie(item.superficie)
    coincidentes = [
        h for h in pieza.hallazgos
        if _superficies_coinciden(h.superficie, objetivo)
        # Un trabajo previo en otra cara no forma parte de este tratamiento.
        and (h.estado_clinico != EstadoClinicoHallazgoEnum.EXISTENTE_PREVIO or h.superficie == objetivo)
    ]

    if coincidentes:
        principal = coincidentes[0]
        principal.superficie = objetivo
        principal.estado_clinico = EstadoClinicoHallazgoEnum.REALIZADO_EN_CLINICA
        principal.color_hex = COLOR_REALIZADO
        principal.detalle = detalle
        if resultado.condicion:
            principal.condicion = resultado.condicion
        for extra in coincidentes[1:]:
            if extra.superficie == objetivo or extra.color_hex == COLOR_PENDIENTE:
                db.delete(extra)
            else:
                extra.estado_clinico = EstadoClinicoHallazgoEnum.REALIZADO_EN_CLINICA
                extra.color_hex = COLOR_REALIZADO
    elif resultado.condicion:
        db.add(HallazgoSuperficie(
            pieza_dental_id=pieza.id,
            superficie=objetivo,
            condicion=resultado.condicion,
            estado_clinico=EstadoClinicoHallazgoEnum.REALIZADO_EN_CLINICA,
            color_hex=COLOR_REALIZADO,
            detalle=detalle,
        ))

    db.flush()
    db.expire(pieza, ["hallazgos"])
