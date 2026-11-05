"""Anulación de pagos: el pago no se borra, queda marcado con su motivo y deja de contar."""
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.sql import func
from sqlalchemy.orm import Session

from app.models import (
    AuditoriaAccionEnum, AuditoriaLog, CajaSesion, CategoriaEgresoCajaEnum, EgresoCaja,
    EstadoCajaEnum, EstadoCobroCitaEnum, MetodoPagoEnum, Pago,
)
from app.services.gaveta import efectivo_en_gaveta, exigir_efectivo


def _actualizar_esperado(caja: CajaSesion) -> None:
    caja.saldo_efectivo_esperado = efectivo_en_gaveta(caja)


def _validar_efectivo(caja: CajaSesion, monto: Decimal) -> None:
    exigir_efectivo(caja, monto, "devolver")


def _revertir_caja(pago: Pago, usuario_id: UUID, db: Session) -> None:
    """
    Un pago con tarjeta o transferencia no tocó la gaveta. El efectivo de la caja abierta se
    descuenta de sus ingresos. El de una caja ya cerrada no altera ese arqueo: se devuelve
    desde la caja abierta como un egreso identificado.
    """
    if pago.metodo_pago != MetodoPagoEnum.EFECTIVO:
        return

    sesion = pago.caja_sesion
    if sesion and sesion.estado == EstadoCajaEnum.ABIERTA:
        _validar_efectivo(sesion, pago.monto)
        sesion.total_ingresos_efectivo -= pago.monto
        _actualizar_esperado(sesion)
        return

    caja = db.query(CajaSesion).filter(CajaSesion.estado == EstadoCajaEnum.ABIERTA).first()
    if not caja:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este pago en efectivo es de una caja ya cerrada: abre la caja para registrar la devolución"
        )
    _validar_efectivo(caja, pago.monto)
    db.add(EgresoCaja(
        caja_sesion_id=caja.id,
        usuario_autoriza_id=usuario_id,
        pago_anulado_id=pago.id,
        categoria=CategoriaEgresoCajaEnum.OTRO,
        monto=pago.monto,
        concepto_motivo="Devolución por anulación de pago",
    ))
    caja.total_egresos_efectivo += pago.monto
    _actualizar_esperado(caja)


def anular_pago(pago: Pago, motivo: str, usuario_id: UUID, db: Session) -> None:
    """
    Un pago que salió de la cuenta de una cita se anula junto con los demás de esa cuenta,
    que vuelve a quedar pendiente para corregirla y cobrarla otra vez.
    """
    if pago.anulado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este pago ya fue anulado")

    cobro = pago.cobro_cita
    pagos = [p for p in cobro.pagos if not p.anulado] if cobro else [pago]

    for actual in pagos:
        _revertir_caja(actual, usuario_id, db)
        actual.anulado = True
        actual.motivo_anulacion = motivo
        actual.fecha_anulacion = func.now()
        actual.anulado_por_usuario_id = usuario_id
        db.add(AuditoriaLog(
            usuario_id=usuario_id,
            tabla_afectada="pagos",
            registro_id=actual.id,
            accion=AuditoriaAccionEnum.UPDATE,
            seccion_consultada="ANULACION_PAGO",
            datos_previos={"anulado": False, "monto": str(actual.monto), "metodo_pago": actual.metodo_pago.value},
            datos_nuevos={"anulado": True, "motivo": motivo},
        ))

    if cobro:
        cobro.estado = EstadoCobroCitaEnum.PENDIENTE
        cobro.cerrado_por_usuario_id = None
        cobro.fecha_cierre = None
        db.add(AuditoriaLog(
            usuario_id=usuario_id,
            tabla_afectada="cobros_cita",
            registro_id=cobro.id,
            accion=AuditoriaAccionEnum.UPDATE,
            seccion_consultada="COBRO_CITA_REABIERTO",
            datos_nuevos={"motivo": motivo},
        ))
