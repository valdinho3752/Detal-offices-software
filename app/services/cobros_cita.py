"""Cuenta de cobro de una cita: se crea al finalizarla y se paga al confirmarla."""
from collections import defaultdict
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.models import (
    AuditoriaAccionEnum, AuditoriaLog, CajaSesion, Cita, CobroCita, CobroCitaLinea, Doctor,
    EstadoCajaEnum, EstadoCobroCitaEnum, ItemPlanTratamiento, MetodoPagoEnum, Pago,
)
from app.models.cobro_cita import ESTADOS_PLAN_CON_DEUDA
from app.services.moneda import texto_moneda
from app.services.nomina import porcentaje_vigente
from app.services.saldos import calcular_saldo_paciente, validar_monto_cobro
from app.services.tratamiento_clinico import describir_procedimiento


def _auditar(usuario_id, cobro: CobroCita, accion, seccion: str, previos=None, nuevos=None) -> AuditoriaLog:
    return AuditoriaLog(
        usuario_id=usuario_id,
        tabla_afectada="cobros_cita",
        registro_id=cobro.id,
        accion=accion,
        seccion_consultada=seccion,
        datos_previos=previos,
        datos_nuevos=nuevos,
    )


def _resumen_lineas(cobro: CobroCita) -> dict:
    return {
        "lineas": [{"concepto": l.concepto, "monto": str(l.monto)} for l in cobro.lineas],
        "total": str(cobro.total),
    }


def _pagado_en_plan(plan_id: UUID, db: Session) -> Decimal:
    return Decimal(db.query(func.coalesce(func.sum(Pago.monto), 0)).filter(
        Pago.plan_id == plan_id, Pago.anulado.is_(False)
    ).scalar())


def crear_cobro_de_cita(cita: Cita, items: List[ItemPlanTratamiento], usuario_id: UUID, db: Session) -> Optional[CobroCita]:
    """
    Crea la cuenta de la cita, una vez por cita. Lo que ya se abonó al plan no se vuelve a
    cobrar: cada línea propone como máximo el saldo pendiente, y conserva su costo como referencia.
    """
    if db.query(CobroCita.id).filter(CobroCita.cita_id == cita.id).first():
        return None

    disponible_paciente = calcular_saldo_paciente(cita.paciente_id, db).pendiente
    disponible_plan = {}
    lineas = []

    for item in items:
        # Un tratamiento repartido en varias citas se cobra una sola vez
        ya_facturado = db.query(CobroCitaLinea.id).join(CobroCita).filter(
            CobroCitaLinea.item_plan_id == item.id,
            CobroCita.estado != EstadoCobroCitaEnum.ANULADO,
        ).first()
        if ya_facturado:
            continue

        costo = Decimal(item.costo_acordado or 0)
        monto = costo
        if item.plan and item.plan.estado in ESTADOS_PLAN_CON_DEUDA:
            if item.plan_id not in disponible_plan:
                disponible_plan[item.plan_id] = Decimal(item.plan.costo_total or 0) - _pagado_en_plan(item.plan_id, db)
            monto = max(min(costo, disponible_plan[item.plan_id], disponible_paciente), Decimal("0"))
            disponible_plan[item.plan_id] -= monto
            disponible_paciente -= monto
        lineas.append(CobroCitaLinea(item_plan_id=item.id, concepto=describir_procedimiento(item)[:255], monto=monto, costo_referencia=costo))

    if not lineas:
        tratamiento = cita.tratamiento
        monto = Decimal(tratamiento.costo_base) if tratamiento else Decimal("0")
        concepto = tratamiento.nombre if tratamiento else cita.motivo_consulta
        lineas.append(CobroCitaLinea(concepto=concepto[:255], monto=monto))

    cobro = CobroCita(cita_id=cita.id, paciente_id=cita.paciente_id, doctor_id=cita.doctor_id, lineas=lineas)
    db.add(cobro)
    db.flush()
    db.add(_auditar(usuario_id, cobro, AuditoriaAccionEnum.INSERT, "COBRO_CITA_CREADO", nuevos=_resumen_lineas(cobro)))
    return cobro


def obtener_cobro_pendiente(cobro_id: UUID, db: Session) -> CobroCita:
    # El bloqueo evita que dos usuarios confirmen la misma cuenta a la vez
    cobro = db.query(CobroCita).filter(CobroCita.id == cobro_id).with_for_update().first()
    if not cobro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cobro no encontrado")
    if cobro.estado != EstadoCobroCitaEnum.PENDIENTE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este cobro ya fue cerrado y no se puede modificar")
    return cobro


def actualizar_lineas(cobro: CobroCita, lineas, usuario_id: UUID, db: Session) -> None:
    previos = _resumen_lineas(cobro)
    existentes = {linea.id: linea for linea in cobro.lineas}
    nuevas = []
    for entrada in lineas:
        if entrada.id:
            linea = existentes.get(entrada.id)
            if not linea:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Una de las líneas no pertenece a este cobro")
            linea.concepto = entrada.concepto
            linea.monto = entrada.monto
        else:
            linea = CobroCitaLinea(concepto=entrada.concepto, monto=entrada.monto)
        nuevas.append(linea)
    cobro.lineas = nuevas
    db.flush()
    nuevos = _resumen_lineas(cobro)
    if nuevos != previos:
        db.add(_auditar(usuario_id, cobro, AuditoriaAccionEnum.UPDATE, "COBRO_CITA_EDITADO", previos, nuevos))


def confirmar_pago(cobro: CobroCita, datos, usuario_id: UUID, db: Session) -> None:
    """
    Registra el pago. Las líneas de un plan aprobado abonan a ese plan, con su mismo límite de
    saldo; las demás son un cobro directo, porque ese tratamiento no forma parte de una deuda aceptada.
    """
    if datos.lineas:
        actualizar_lineas(cobro, datos.lineas, usuario_id, db)
    if cobro.total <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El total es {texto_moneda(0, db)}: cierra el cobro sin pago e indica el motivo"
        )

    doctor_id = datos.doctor_comision_id
    if doctor_id and not db.query(Doctor.id).filter(Doctor.id == doctor_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor no encontrado")

    caja = db.query(CajaSesion).filter(CajaSesion.estado == EstadoCajaEnum.ABIERTA).first()
    if not caja:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se puede registrar un cobro si no hay una caja abierta")

    por_plan = defaultdict(Decimal)
    directas = []
    for linea in cobro.lineas:
        if linea.monto <= 0:
            continue
        plan = linea.plan_con_deuda
        if plan:
            por_plan[plan.id] += linea.monto
        else:
            directas.append(linea)

    def registrar(monto: Decimal, plan_id, es_directo: bool, detalle: str):
        nota = f"{detalle} | {datos.observaciones.strip()}" if (datos.observaciones or "").strip() else detalle
        pago = Pago(
            paciente_id=cobro.paciente_id,
            plan_id=plan_id,
            cobro_cita_id=cobro.id,
            caja_sesion_id=caja.id,
            doctor_comision_id=doctor_id,
            porcentaje_comision=porcentaje_vigente(doctor_id, db),
            registrado_por_usuario_id=usuario_id,
            monto=monto,
            metodo_pago=datos.metodo_pago,
            referencia_comprobante=datos.referencia_comprobante or None,
            es_cobro_directo=es_directo,
            observaciones=nota,
        )
        db.add(pago)
        db.flush()
        db.add(AuditoriaLog(
            usuario_id=usuario_id,
            tabla_afectada="pagos",
            registro_id=pago.id,
            accion=AuditoriaAccionEnum.INSERT,
            seccion_consultada="REGISTRO_PAGO_COBRO_CITA",
        ))
        if datos.metodo_pago == MetodoPagoEnum.EFECTIVO:
            caja.total_ingresos_efectivo += monto
            caja.saldo_efectivo_esperado = caja.monto_inicial_fondo + caja.total_ingresos_efectivo - caja.total_egresos_efectivo

    for plan_id, monto in por_plan.items():
        validar_monto_cobro(cobro.paciente_id, plan_id, monto, db)
        conceptos = ", ".join(l.concepto for l in cobro.lineas if l.monto > 0 and l.plan_con_deuda and l.plan_con_deuda.id == plan_id)
        registrar(monto, plan_id, False, f"Cobro de cita: {conceptos}")
    if directas:
        conceptos = ", ".join(l.concepto for l in directas)
        registrar(sum((l.monto for l in directas), Decimal("0")), None, True, f"Cobro de cita: {conceptos}")

    cobro.estado = EstadoCobroCitaEnum.PAGADO
    cobro.cerrado_por_usuario_id = usuario_id
    cobro.fecha_cierre = func.now()
    db.add(_auditar(usuario_id, cobro, AuditoriaAccionEnum.UPDATE, "COBRO_CITA_PAGADO", nuevos=_resumen_lineas(cobro)))


def cerrar_sin_pago(cobro: CobroCita, motivo: str, usuario_id: UUID, db: Session) -> None:
    cobro.estado = EstadoCobroCitaEnum.ANULADO
    cobro.motivo_cierre = motivo
    cobro.cerrado_por_usuario_id = usuario_id
    cobro.fecha_cierre = func.now()
    db.add(_auditar(usuario_id, cobro, AuditoriaAccionEnum.UPDATE, "COBRO_CITA_SIN_PAGO", nuevos={"motivo": motivo, **_resumen_lineas(cobro)}))
