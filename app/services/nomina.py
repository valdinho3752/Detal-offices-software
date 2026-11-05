"""Saldo de cada empleado: comisiones generadas, lo ya pagado y los adelantos por recuperar."""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ContratoRemuneracion, Doctor, Pago, PagoEmpleado, TipoPagoEmpleadoEnum, Usuario

CENTAVO = Decimal("0.01")
TIPOS_SUELDO = (TipoPagoEmpleadoEnum.SUELDO_MENSUAL, TipoPagoEmpleadoEnum.QUINCENA)


@dataclass(frozen=True)
class Liquidacion:
    contrato: Optional[ContratoRemuneracion]
    salario_base: Decimal
    porcentaje_comision: Decimal
    total_cobrado: Decimal
    comision_bruta: Decimal
    comisiones_liquidadas: Decimal
    adelantos_entregados: Decimal
    adelantos_descontados_en_sueldo: Decimal

    @property
    def adelantos_pendientes(self) -> Decimal:
        return self.adelantos_entregados - self.adelantos_descontados_en_sueldo

    @property
    def saldo_comision(self) -> Decimal:
        """Negativo si se pagó de más, por ejemplo tras anular un cobro: se compensa con comisiones futuras."""
        return self.comision_bruta - self.comisiones_liquidadas - self.adelantos_pendientes


def _suma(columna, db: Session, *filtros) -> Decimal:
    return Decimal(db.query(func.coalesce(func.sum(columna), 0)).filter(*filtros).scalar())


def porcentaje_vigente(doctor_id: Optional[UUID], db: Session) -> Decimal:
    """Porcentaje que se guarda en cada cobro: cambiar el contrato después no altera ese cobro."""
    if not doctor_id:
        return Decimal("0")
    porcentaje = (
        db.query(ContratoRemuneracion.porcentaje_comision)
        .join(Doctor, Doctor.usuario_id == ContratoRemuneracion.usuario_id)
        .filter(Doctor.id == doctor_id)
        .scalar()
    )
    return Decimal(porcentaje or 0)


def calcular_liquidacion(usuario: Usuario, db: Session) -> Liquidacion:
    contrato = db.query(ContratoRemuneracion).filter(ContratoRemuneracion.usuario_id == usuario.id).first()
    porcentaje = Decimal(contrato.porcentaje_comision) if contrato else Decimal("0")

    total_cobrado = comision_bruta = Decimal("0")
    if usuario.doctor_perfil:
        cobros = (Pago.doctor_comision_id == usuario.doctor_perfil.id, Pago.anulado.is_(False))
        total_cobrado = _suma(Pago.monto, db, *cobros)
        comision_bruta = _suma(Pago.monto * Pago.porcentaje_comision / 100, db, *cobros)

    return Liquidacion(
        contrato=contrato,
        salario_base=Decimal(contrato.salario_base) if contrato else Decimal("0"),
        porcentaje_comision=porcentaje,
        total_cobrado=total_cobrado,
        comision_bruta=comision_bruta.quantize(CENTAVO),
        comisiones_liquidadas=_suma(PagoEmpleado.monto_comisiones, db, PagoEmpleado.usuario_empleado_id == usuario.id),
        adelantos_entregados=_suma(
            PagoEmpleado.monto_neto_pagado, db,
            PagoEmpleado.usuario_empleado_id == usuario.id,
            PagoEmpleado.tipo_pago == TipoPagoEmpleadoEnum.ADELANTO,
        ),
        adelantos_descontados_en_sueldo=_suma(
            PagoEmpleado.deducciones_descuentos, db,
            PagoEmpleado.usuario_empleado_id == usuario.id,
            PagoEmpleado.tipo_pago.in_(TIPOS_SUELDO),
        ),
    )
