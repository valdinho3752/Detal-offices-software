from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import (
    ContratoRemuneracion, PagoEmpleado, EgresoCaja, CajaSesion,
    Doctor, Usuario, CategoriaEgresoCajaEnum, EstadoCajaEnum,
    TipoPagoEmpleadoEnum, AuditoriaLog, AuditoriaAccionEnum
)
from app.core.dependencies import get_current_user, require_permission, tiene_permiso
from app.schemas.pago_empleado import PagoEmpleadoCreate, PagoEmpleadoResponse
from app.services.gaveta import exigir_efectivo
from app.services.moneda import texto_moneda
from app.services.nomina import TIPOS_SUELDO, Liquidacion, calcular_liquidacion

router = APIRouter(prefix="/empleados", tags=["Nómina, Sueldos y Comisiones de Empleados"])

def _resumen_personal(usuario: Usuario, contrato: Optional[ContratoRemuneracion]) -> dict:
    doctor = usuario.doctor_perfil
    return {
        "usuario_id": str(usuario.id),
        "nombre_completo": f"{usuario.nombre} {usuario.apellido}",
        "activo": usuario.activo,
        "rol": usuario.rol.nombre if usuario.rol else "",
        "doctor_id": str(doctor.id) if doctor else None,
        "especialidad": doctor.especialidad if doctor else None,
        "numero_colegiatura": doctor.numero_colegiatura if doctor else None,
        "contrato": {
            "id": str(contrato.id),
            "tipo_remuneracion": contrato.tipo_remuneracion.value,
            "salario_base": float(contrato.salario_base),
            "porcentaje_comision": float(contrato.porcentaje_comision),
            "valor_hora": float(contrato.valor_hora),
        } if contrato else None,
    }

def _resumen_liquidacion(liquidacion: Liquidacion) -> dict:
    return {
        "salario_base": float(liquidacion.salario_base),
        "porcentaje_pactado": float(liquidacion.porcentaje_comision),
        "total_cobrado_por_sus_tratamientos": float(liquidacion.total_cobrado),
        "comision_bruta_generada": float(liquidacion.comision_bruta),
        "comisiones_ya_liquidadas": float(liquidacion.comisiones_liquidadas),
        "adelantos_entregados": float(liquidacion.adelantos_entregados),
        "adelantos_descontados_en_sueldo": float(liquidacion.adelantos_descontados_en_sueldo),
        "total_anticipos": float(liquidacion.adelantos_pendientes),
        "saldo_comision_por_pagar": float(liquidacion.saldo_comision),
    }

def _validar_montos_con_saldo(datos: PagoEmpleadoCreate, liquidacion: Liquidacion, db: Session) -> None:
    if datos.tipo_pago == TipoPagoEmpleadoEnum.COMISION_TRATAMIENTOS and datos.monto_neto_pagado > liquidacion.saldo_comision:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La comisión no puede superar el saldo por pagar de {texto_moneda(max(liquidacion.saldo_comision, Decimal('0')), db)}"
        )
    if datos.deducciones_descuentos > liquidacion.adelantos_pendientes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede descontar más que los adelantos pendientes de {texto_moneda(liquidacion.adelantos_pendientes, db)}"
        )

@router.get("/personal")
def listar_personal(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Personal activo y su contrato, más quien ya no trabaja aquí pero aún tiene comisión por cobrar:
    esa deuda no debe perderse de vista. Sin permiso de consulta general, solo los datos propios.
    """
    if tiene_permiso(current_user, "EMPLEADOS_READ", db):
        usuarios = (
            db.query(Usuario)
            .options(joinedload(Usuario.doctor_perfil), joinedload(Usuario.rol))
            .order_by(Usuario.nombre, Usuario.apellido)
            .all()
        )
        usuarios = [u for u in usuarios if u.activo or calcular_liquidacion(u, db).saldo_comision > 0]
    else:
        usuarios = [current_user]
    contratos = {
        c.usuario_id: c
        for c in db.query(ContratoRemuneracion).filter(ContratoRemuneracion.usuario_id.in_([u.id for u in usuarios]))
    }
    return [_resumen_personal(u, contratos.get(u.id)) for u in usuarios]

@router.get("/liquidacion/{usuario_id}")
def obtener_liquidacion(
    usuario_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if usuario_id != current_user.id and not tiene_permiso(current_user, "EMPLEADOS_READ", db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo puedes consultar tu propia liquidación")
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return _resumen_liquidacion(calcular_liquidacion(usuario, db))

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
    # El bloqueo evita que dos pagos simultáneos superen juntos el saldo disponible
    empleado = db.query(Usuario).filter(Usuario.id == datos.usuario_empleado_id).with_for_update(of=Usuario).first()
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    entrega_efectivo = datos.metodo_pago == "EFECTIVO_CAJA" and datos.monto_neto_pagado > 0
    caja = None
    if entrega_efectivo:
        caja = db.query(CajaSesion).filter(CajaSesion.estado == EstadoCajaEnum.ABIERTA).with_for_update().first()
        if not caja:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede pagar en efectivo de caja si no hay una caja abierta"
            )
        exigir_efectivo(caja, datos.monto_neto_pagado, "pagar")

    _validar_montos_con_saldo(datos, calcular_liquidacion(empleado, db), db)

    valores = datos.model_dump()
    if datos.tipo_pago == TipoPagoEmpleadoEnum.COMISION_TRATAMIENTOS:
        valores["monto_comisiones"] = datos.monto_neto_pagado
    if datos.tipo_pago in TIPOS_SUELDO and datos.monto_base == 0:
        valores["monto_base"] = datos.monto_neto_pagado + datos.deducciones_descuentos

    pago = PagoEmpleado(**valores, usuario_autoriza_id=current_user.id)
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

    return {
        "doctor_id": str(doctor.id),
        "doctor": f"{doctor.usuario.nombre} {doctor.usuario.apellido}",
        **_resumen_liquidacion(calcular_liquidacion(doctor.usuario, db)),
    }
