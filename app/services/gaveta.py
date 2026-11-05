"""Efectivo físico de la caja abierta: no puede salir más dinero del que hay."""
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import object_session

from app.models import CajaSesion
from app.services.moneda import texto_moneda


def efectivo_en_gaveta(caja: CajaSesion) -> Decimal:
    return caja.monto_inicial_fondo + caja.total_ingresos_efectivo - caja.total_egresos_efectivo


def exigir_efectivo(caja: CajaSesion, monto: Decimal, accion: str) -> None:
    disponible = efectivo_en_gaveta(caja)
    if monto > disponible:
        db = object_session(caja)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No hay efectivo suficiente en la gaveta para {accion} {texto_moneda(monto, db)}: quedan {texto_moneda(disponible, db)}"
        )
