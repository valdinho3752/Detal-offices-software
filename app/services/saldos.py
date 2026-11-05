"""Saldo de los pacientes y límite de los cobros."""
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import EstadoPlanEnum, Paciente, Pago, PlanTratamiento
from app.services.moneda import texto_moneda

# Solo generan deuda los planes aceptados: un presupuesto PROPUESTO aún no es un compromiso de pago
ESTADOS_PLAN_CON_DEUDA = (EstadoPlanEnum.APROBADO, EstadoPlanEnum.EN_CURSO, EstadoPlanEnum.COMPLETADO)


@dataclass(frozen=True)
class SaldoPaciente:
    total_presupuestado: Decimal
    total_pagado: Decimal

    @property
    def pendiente(self) -> Decimal:
        return self.total_presupuestado - self.total_pagado


def calcular_saldo_paciente(paciente_id: UUID, db: Session) -> SaldoPaciente:
    presupuestado = db.query(func.coalesce(func.sum(PlanTratamiento.costo_total), 0)).filter(
        PlanTratamiento.paciente_id == paciente_id,
        PlanTratamiento.estado.in_(ESTADOS_PLAN_CON_DEUDA),
    ).scalar()
    # Un cobro directo paga una consulta aparte: no reduce lo que se debe por los planes
    pagado = db.query(func.coalesce(func.sum(Pago.monto), 0)).filter(
        Pago.paciente_id == paciente_id,
        Pago.es_cobro_directo.is_(False),
        Pago.anulado.is_(False),
    ).scalar()
    return SaldoPaciente(Decimal(presupuestado), Decimal(pagado))


def _rechazar(monto: Decimal, disponible: Decimal, contexto: str, db: Session):
    if disponible <= 0:
        detalle = f"No se puede registrar el cobro: {contexto} no tiene saldo pendiente"
    else:
        detalle = f"El cobro de {texto_moneda(monto, db)} supera el saldo pendiente de {texto_moneda(disponible, db)} de {contexto}"
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detalle)


def validar_cobro_directo(paciente_id: UUID, plan_id, concepto, db: Session) -> None:
    """Una consulta se cobra sin plan aprobado, pero debe quedar claro qué se cobró."""
    if plan_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un cobro directo no se aplica a un plan: elige un abono al plan o quita el plan"
        )
    if not (concepto or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Indica el concepto del cobro directo, por ejemplo Consulta general"
        )
    if not db.query(Paciente.id).filter(Paciente.id == paciente_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")


def validar_monto_cobro(paciente_id: UUID, plan_id, monto: Decimal, db: Session) -> None:
    """Un cobro o adelanto nunca puede superar lo que el paciente aún debe por sus planes aprobados."""
    # El bloqueo evita que dos cobros simultáneos superen juntos el saldo.
    paciente = db.query(Paciente).filter(Paciente.id == paciente_id).with_for_update().first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    if plan_id:
        plan = db.query(PlanTratamiento).filter(
            PlanTratamiento.id == plan_id, PlanTratamiento.paciente_id == paciente_id
        ).first()
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El plan no pertenece a este paciente")
        if plan.estado not in ESTADOS_PLAN_CON_DEUDA:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se puede cobrar sobre un plan de tratamiento aprobado"
            )
        pagado_plan = db.query(func.coalesce(func.sum(Pago.monto), 0)).filter(
            Pago.plan_id == plan_id, Pago.anulado.is_(False)
        ).scalar()
        disponible_plan = Decimal(plan.costo_total) - Decimal(pagado_plan)
        if monto > disponible_plan:
            _rechazar(monto, disponible_plan, "este plan", db)

    disponible = calcular_saldo_paciente(paciente_id, db).pendiente
    if monto > disponible:
        _rechazar(monto, disponible, "este paciente", db)
