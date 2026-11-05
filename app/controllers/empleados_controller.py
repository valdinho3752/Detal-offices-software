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
from app.core.dependencies import get_current_user, require_role
from app.schemas.pago_empleado import PagoEmpleadoCreate, PagoEmpleadoResponse

router = APIRouter(prefix="/empleados", tags=["Nómina, Sueldos y Comisiones de Empleados"])

@router.get("/pagos", response_model=List[PagoEmpleadoResponse])
def listar_pagos_empleados(
    usuario_empleado_id: Optional[UUID] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(PagoEmpleado)
    # Si no es admin, solo ve sus propios pagos
    rol_actual = str(current_user.rol.codigo.value if hasattr(current_user.rol.codigo, "value") else current_user.rol.codigo).upper()
    if rol_actual != "ADMIN":
        query = query.filter(PagoEmpleado.usuario_empleado_id == current_user.id)
    elif usuario_empleado_id:
        query = query.filter(PagoEmpleado.usuario_empleado_id == usuario_empleado_id)
    return query.order_by(PagoEmpleado.fecha_hora_pago.desc()).all()

@router.post("/pagos", response_model=PagoEmpleadoResponse, status_code=status.HTTP_201_CREATED)
def registrar_pago_empleado(
    datos: PagoEmpleadoCreate,
    current_user: Usuario = Depends(require_role(RolCodigoEnum.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Registra pago de sueldo, adelanto o comisión.
    Si se paga en efectivo desde caja, genera el egreso físico automático en la sesión de caja abierta.
    """
    pago = PagoEmpleado(
        **datos.model_dump(),
        usuario_autoriza_id=current_user.id
    )
    db.add(pago)
    db.flush()

    # Si salió en efectivo y hay caja abierta, registrar egreso automático en gaveta
    if datos.metodo_pago == "EFECTIVO_CAJA":
        caja = db.query(CajaSesion).filter(CajaSesion.estado == EstadoCajaEnum.ABIERTA).first()
        if caja:
            pago.caja_sesion_id = caja.id
            egreso = EgresoCaja(
                caja_sesion_id=caja.id,
                usuario_autoriza_id=current_user.id,
                usuario_beneficiario_id=datos.usuario_empleado_id,
                pago_empleado_id=pago.id,
                categoria=CategoriaEgresoCajaEnum.ADELANTO_SUELDO if datos.tipo_pago == TipoPagoEmpleadoEnum.ADELANTO else CategoriaEgresoCajaEnum.PAGO_SUELDO,
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

    # Contrato del doctor
    contrato = db.query(ContratoRemuneracion).filter(ContratoRemuneracion.usuario_id == doctor.usuario_id).first()
    porcentaje = float(contrato.porcentaje_comision) if contrato else 0.0

    # Total recaudado por tratamientos asignados a este doctor
    total_cobrado = db.query(func.coalesce(func.sum(Pago.monto), 0)).filter(
        Pago.doctor_comision_id == doctor.id
    ).scalar()

    comision_generada = float(total_cobrado) * (porcentaje / 100.0)

    # Total ya pagado al doctor en comisiones
    comisiones_ya_pagadas = db.query(func.coalesce(func.sum(PagoEmpleado.monto_comisiones), 0)).filter(
        PagoEmpleado.usuario_empleado_id == doctor.usuario_id
    ).scalar()

    saldo_comision_pendiente = comision_generada - float(comisiones_ya_pagadas)

    return {
        "doctor_id": str(doctor.id),
        "doctor": f"{doctor.usuario.nombre} {doctor.usuario.apellido}",
        "porcentaje_pactado": porcentaje,
        "total_cobrado_por_sus_tratamientos": float(total_cobrado),
        "comision_bruta_generada": comision_generada,
        "comisiones_ya_liquidadas": float(comisiones_ya_pagadas),
        "saldo_comision_por_pagar": saldo_comision_pendiente
    }
