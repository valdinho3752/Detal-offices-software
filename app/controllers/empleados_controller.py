from typing import List, Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import (
    PagoEmpleado, EgresoCaja, CajaSesion, ContratoRemuneracion,
    Pago, Doctor, Usuario, RolCodigoEnum, CategoriaEgresoCajaEnum, EstadoCajaEnum,
    TipoPagoEmpleadoEnum, AuditoriaLog, AuditoriaAccionEnum
)
from app.core.dependencies import get_current_user, require_permission, tiene_permiso
from app.schemas.pago_empleado import PagoEmpleadoCreate, PagoEmpleadoResponse

router = APIRouter(prefix="/empleados", tags=["Nómina, Sueldos y Comisiones de Empleados"])

@router.get("/pagos", response_model=List[PagoEmpleadoResponse])
def listar_pagos_empleados(
    usuario_empleado_id: Optional[UUID] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(PagoEmpleado)
    # Sin permiso de consulta general, cada empleado solo ve sus propios pagos
    if not tiene_permiso(current_user, "EMPLEADOS_READ", db):
        query = query.filter(PagoEmpleado.usuario_empleado_id == current_user.id)
    elif usuario_empleado_id:
        query = query.filter(PagoEmpleado.usuario_empleado_id == usuario_empleado_id)
    return query.order_by(PagoEmpleado.fecha_hora_pago.desc()).all()

@router.post("/pagos", response_model=PagoEmpleadoResponse, status_code=status.HTTP_201_CREATED)
def registrar_pago_empleado(
    datos: PagoEmpleadoCreate,
    current_user: Usuario = Depends(require_permission("EMPLEADOS_PAGOS")),
    db: Session = Depends(get_db)
):
    """
    Registra pago de sueldo, adelanto o comisión.
    Si se paga en efectivo desde caja, genera el egreso físico automático en la sesión de caja abierta.
    """
    caja = None
    if datos.metodo_pago == "EFECTIVO_CAJA":
        caja = db.query(CajaSesion).filter(CajaSesion.estado == EstadoCajaEnum.ABIERTA).first()
        if not caja:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede pagar en efectivo de caja si no hay una caja abierta"
            )

    pago = PagoEmpleado(
        **datos.model_dump(),
        usuario_autoriza_id=current_user.id
    )
    db.add(pago)
    db.flush()

    # Un pago en efectivo genera el egreso automático en la gaveta
    if caja:
        categorias_egreso = {
            TipoPagoEmpleadoEnum.ADELANTO: CategoriaEgresoCajaEnum.ADELANTO_SUELDO,
            TipoPagoEmpleadoEnum.COMISION_TRATAMIENTOS: CategoriaEgresoCajaEnum.COMISION_DOCTOR,
        }
        pago.caja_sesion_id = caja.id
        egreso = EgresoCaja(
            caja_sesion_id=caja.id,
            usuario_autoriza_id=current_user.id,
            usuario_beneficiario_id=datos.usuario_empleado_id,
            pago_empleado_id=pago.id,
            categoria=categorias_egreso.get(datos.tipo_pago, CategoriaEgresoCajaEnum.PAGO_SUELDO),
            monto=datos.monto_neto_pagado,
            concepto_motivo=f"Pago nómina/adelanto: {datos.tipo_pago.value}"
        )
        db.add(egreso)
        caja.total_egresos_efectivo += datos.monto_neto_pagado
        caja.saldo_efectivo_esperado = caja.monto_inicial_fondo + caja.total_ingresos_efectivo - caja.total_egresos_efectivo

    log = AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="pagos_empleados",
        registro_id=pago.id,
        accion=AuditoriaAccionEnum.INSERT,
        seccion_consultada="PAGO_NOMINA_EMPLEADO"
    )
    db.add(log)
    db.commit()
    db.refresh(pago)
    return pago

@router.get("/comisiones-doctor/{doctor_id}")
def calcular_comisiones_doctor(
    doctor_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calcula la producción y comisiones acumuladas del doctor según su contrato salarial.
    """
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor no encontrado")
    if doctor.usuario_id != current_user.id and not tiene_permiso(current_user, "EMPLEADOS_READ", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes consultar tus propias comisiones"
        )

    # Contrato del doctor
    contrato = db.query(ContratoRemuneracion).filter(ContratoRemuneracion.usuario_id == doctor.usuario_id).first()
    porcentaje = float(contrato.porcentaje_comision) if contrato else 0.0

    # Total recaudado por tratamientos asignados a este doctor
    total_cobrado = db.query(func.coalesce(func.sum(Pago.monto), 0)).filter(
        Pago.doctor_comision_id == doctor.id,
        Pago.anulado.is_(False),
    ).scalar()

    comision_generada = float(total_cobrado) * (porcentaje / 100.0)

    # Total ya pagado al doctor en comisiones
    comisiones_ya_pagadas = db.query(func.coalesce(func.sum(PagoEmpleado.monto_comisiones), 0)).filter(
        PagoEmpleado.usuario_empleado_id == doctor.usuario_id
    ).scalar()

    # Los anticipos ya entregados al doctor se descuentan de lo que falta por pagarle
    anticipos = db.query(func.coalesce(func.sum(PagoEmpleado.monto_neto_pagado), 0)).filter(
        PagoEmpleado.usuario_empleado_id == doctor.usuario_id,
        PagoEmpleado.tipo_pago == TipoPagoEmpleadoEnum.ADELANTO,
    ).scalar()

    saldo_comision_pendiente = comision_generada - float(comisiones_ya_pagadas) - float(anticipos)

    return {
        "doctor_id": str(doctor.id),
        "doctor": f"{doctor.usuario.nombre} {doctor.usuario.apellido}",
        "porcentaje_pactado": porcentaje,
        "total_cobrado_por_sus_tratamientos": float(total_cobrado),
        "comision_bruta_generada": comision_generada,
        "comisiones_ya_liquidadas": float(comisiones_ya_pagadas),
        "total_anticipos": float(anticipos),
        "saldo_comision_por_pagar": saldo_comision_pendiente
    }
