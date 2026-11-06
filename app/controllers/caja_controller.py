from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.database import get_db
from app.models import (
    CajaSesion, Pago, EgresoCaja, EstadoCajaEnum, MetodoPagoEnum,
    Usuario, RolCodigoEnum, AuditoriaLog, AuditoriaAccionEnum
)
from app.core.dependencies import get_current_user, require_permission, tiene_permiso
from app.services.anulacion_pagos import anular_pago
from app.services.saldos import validar_cobro_directo, validar_monto_cobro
from app.schemas.caja import (
    CajaAperturaRequest, CajaCierreRequest, CajaSesionResponse,
    PagoAnular, PagoCreate, PagoResponse, EgresoCajaCreate, EgresoCajaResponse
)

from sqlalchemy.exc import IntegrityError
from app.models import Doctor
from app.services.gaveta import exigir_efectivo
from app.services.nomina import porcentaje_vigente

router = APIRouter(prefix="/caja", tags=["Caja Diaria y Finanzas"])

MEDIOS_DE_PAGO = {
    MetodoPagoEnum.EFECTIVO: "Efectivo",
    MetodoPagoEnum.TARJETA_DEBITO: "Tarjeta de débito",
    MetodoPagoEnum.TARJETA_CREDITO: "Tarjeta de crédito",
    MetodoPagoEnum.TRANSFERENCIA: "Transferencia",
    MetodoPagoEnum.OTRO: "Otro medio",
}


def _movimientos_del_turno(caja: CajaSesion, db: Session) -> list:
    """Cobros vigentes y egresos de la sesión, del más reciente al más antiguo."""
    pagos = db.query(Pago).options(joinedload(Pago.paciente)).filter(
        Pago.caja_sesion_id == caja.id, Pago.anulado.is_(False)
    ).all()
    egresos = db.query(EgresoCaja).filter(EgresoCaja.caja_sesion_id == caja.id).all()
    movimientos = [{
        "tipo": "INGRESO",
        "timestamp": pago.fecha_hora,
        "concepto": f"Cobro a {pago.paciente.nombres} {pago.paciente.apellidos} · {MEDIOS_DE_PAGO[pago.metodo_pago]}",
        "comprobante_numero": pago.referencia_comprobante,
        "monto": float(pago.monto),
    } for pago in pagos] + [{
        "tipo": "EGRESO",
        "timestamp": egreso.fecha_hora,
        "concepto": egreso.concepto_motivo,
        "comprobante_numero": egreso.numero_recibo_comprobante,
        "monto": float(egreso.monto),
    } for egreso in egresos]
    return sorted(movimientos, key=lambda m: m["timestamp"], reverse=True)


@router.get("/estado")
def obtener_estado_caja_actual(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Devuelve la sesión de caja activa con el monto real en gaveta calculado en vivo y estado diario:
    - tipo_bloqueo: None (operativo hoy), "APERTURA_REQUERIDA" (hoy no se abrió caja), "CIERRE_PENDIENTE_ANTERIOR" (caja de día previo sin cerrar)
    """
    server_today = db.execute(func.current_date()).scalar()
    caja = db.query(CajaSesion).filter(CajaSesion.estado == EstadoCajaEnum.ABIERTA).first()

    if not caja:
        return {
            "caja_abierta": False,
            "abierta": False,
            "es_del_dia": False,
            "requiere_apertura": True,
            "requiere_cierre_anterior": False,
            "tipo_bloqueo": "APERTURA_REQUERIDA",
            "fecha_servidor": str(server_today),
            "mensaje": f"No hay ninguna caja abierta para la fecha de hoy ({server_today.strftime('%d/%m/%Y')}). Debe realizar la apertura de turno con el fondo inicial."
        }

    # Desglose de ingresos por método de pago de esta sesión
    ingresos_por_metodo = db.query(
        Pago.metodo_pago,
        func.coalesce(func.sum(Pago.monto), 0).label("total")
    ).filter(Pago.caja_sesion_id == caja.id, Pago.anulado.is_(False)).group_by(Pago.metodo_pago).all()

    metodos_dict = {m.value: 0.0 for m in MetodoPagoEnum}
    for metodo, total in ingresos_por_metodo:
        metodos_dict[metodo.value] = float(total)

    efectivo_actual_en_gaveta = float(caja.monto_inicial_fondo) + float(caja.total_ingresos_efectivo) - float(caja.total_egresos_efectivo)

    caja_fecha = caja.fecha_apertura.date() if hasattr(caja.fecha_apertura, "date") else caja.fecha_apertura
    es_del_dia = (caja_fecha == server_today)

    tipo_bloqueo = None
    if not es_del_dia:
        tipo_bloqueo = "CIERRE_PENDIENTE_ANTERIOR"
        mensaje = f"Existe una sesión de caja abierta el {caja.fecha_apertura.strftime('%d/%m/%Y')} sin cerrar. Debe realizar el arqueo y cierre del turno anterior antes de iniciar hoy."
    else:
        mensaje = "Caja del día abierta y operativa."

    # La barrera de apertura aplica a todos, pero los montos solo a quien puede ver la caja
    if not tiene_permiso(current_user, "CAJA_READ", db):
        return {
            "caja_abierta": True,
            "abierta": True,
            "es_del_dia": es_del_dia,
            "requiere_apertura": False,
            "requiere_cierre_anterior": not es_del_dia,
            "tipo_bloqueo": tipo_bloqueo,
            "fecha_servidor": str(server_today),
            "fecha_apertura_str": caja.fecha_apertura.strftime("%d/%m/%Y %H:%M"),
            "mensaje": mensaje
        }

    return {
        "caja_abierta": True,
        "abierta": True,
        "caja_id": str(caja.id),
        "es_del_dia": es_del_dia,
        "requiere_apertura": False,
        "requiere_cierre_anterior": not es_del_dia,
        "tipo_bloqueo": tipo_bloqueo,
        "fecha_servidor": str(server_today),
        "fecha_apertura": caja.fecha_apertura,
        "fecha_apertura_str": caja.fecha_apertura.strftime("%d/%m/%Y %H:%M"),
        "usuario_apertura_nombre": f"{caja.usuario_apertura.nombre} {caja.usuario_apertura.apellido}" if caja.usuario_apertura else "Usuario",
        "fondo_inicial": float(caja.monto_inicial_fondo),
        "monto_apertura": float(caja.monto_inicial_fondo),
        "total_cobrado_efectivo": float(caja.total_ingresos_efectivo),
        "total_ingresos": float(caja.total_ingresos_efectivo),
        "total_egresos_efectivo": float(caja.total_egresos_efectivo),
        "total_egresos": float(caja.total_egresos_efectivo),
        "saldo_en_gaveta": efectivo_actual_en_gaveta,
        "efectivo_actual_en_gaveta": efectivo_actual_en_gaveta,
        "saldo_efectivo_esperado": efectivo_actual_en_gaveta,
        "ingresos_otros_medios": {
            "tarjeta_debito": metodos_dict.get(MetodoPagoEnum.TARJETA_DEBITO.value, 0.0),
            "tarjeta_credito": metodos_dict.get(MetodoPagoEnum.TARJETA_CREDITO.value, 0.0),
            "transferencia": metodos_dict.get(MetodoPagoEnum.TRANSFERENCIA.value, 0.0),
        },
        "total_recaudacion_global_sesion": sum(metodos_dict.values()),
        "movimientos": _movimientos_del_turno(caja, db),
        "mensaje": mensaje
    }

@router.post("/abrir", response_model=CajaSesionResponse, status_code=status.HTTP_201_CREATED)
def abrir_caja(
    datos: CajaAperturaRequest,
    current_user: Usuario = Depends(require_permission("CAJA_APERTURA")),
    db: Session = Depends(get_db)
):
    # Verificar si ya existe una caja abierta
    caja_activa = db.query(CajaSesion).filter(CajaSesion.estado == EstadoCajaEnum.ABIERTA).first()
    if caja_activa:
        server_today = db.execute(func.current_date()).scalar()
        caja_fecha = caja_activa.fecha_apertura.date() if hasattr(caja_activa.fecha_apertura, "date") else caja_activa.fecha_apertura
        if caja_fecha < server_today:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Existe una caja abierta previa del día {caja_activa.fecha_apertura.strftime('%d/%m/%Y')} sin cerrar. Debe realizar el cierre y arqueo previo antes de abrir una nueva sesión."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una sesión de caja abierta en este momento"
        )

    monto_inicial = datos.monto_inicial_fondo if datos.monto_apertura is None else datos.monto_apertura
    if monto_inicial is None:
        monto_inicial = Decimal("0.00")

    nueva_caja = CajaSesion(
        usuario_apertura_id=current_user.id,
        monto_inicial_fondo=monto_inicial,
        saldo_efectivo_esperado=monto_inicial,
        estado=EstadoCajaEnum.ABIERTA,
        observaciones=datos.observaciones
    )
    db.add(nueva_caja)
    try:
        db.flush()
    except IntegrityError:
        # Otra persona abrió la caja en este mismo instante: el índice único lo impide
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe una sesión de caja abierta en este momento")

    log = AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="cajas_sesiones",
        registro_id=nueva_caja.id,
        accion=AuditoriaAccionEnum.INSERT,
        seccion_consultada="APERTURA_CAJA"
    )
    db.add(log)
    db.commit()
    db.refresh(nueva_caja)
    return nueva_caja

@router.post("/cerrar", response_model=CajaSesionResponse)
def cerrar_caja(
    datos: CajaCierreRequest,
    current_user: Usuario = Depends(require_permission("CAJA_CIERRE")),
    db: Session = Depends(get_db)
):
    caja = db.query(CajaSesion).filter(CajaSesion.estado == EstadoCajaEnum.ABIERTA).first()
    if not caja:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hay ninguna sesión de caja abierta para cerrar")

    monto_contado = datos.total_efectivo_contado if datos.monto_cierre_real is None else datos.monto_cierre_real
    if monto_contado is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes indicar el efectivo contado para cerrar la caja"
        )

    saldo_esperado = caja.monto_inicial_fondo + caja.total_ingresos_efectivo - caja.total_egresos_efectivo
    descuadre = monto_contado - saldo_esperado

    caja.usuario_cierre_id = current_user.id
    caja.fecha_cierre = func.now()
    caja.saldo_efectivo_esperado = saldo_esperado
    caja.total_efectivo_contado = monto_contado
    caja.diferencia_descuadre = descuadre
    caja.estado = EstadoCajaEnum.CERRADA
    if datos.observaciones:
        caja.observaciones = (caja.observaciones or "") + "\nCierre: " + datos.observaciones

    log = AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="cajas_sesiones",
        registro_id=caja.id,
        accion=AuditoriaAccionEnum.UPDATE,
        seccion_consultada="CIERRE_CAJA"
    )
    db.add(log)
    db.commit()
    db.refresh(caja)
    return caja

@router.post("/pagos", response_model=PagoResponse, status_code=status.HTTP_201_CREATED)
def registrar_pago_paciente(
    datos: PagoCreate,
    current_user: Usuario = Depends(require_permission("CAJA_PAGOS")),
    db: Session = Depends(get_db)
):
    caja = db.query(CajaSesion).filter(CajaSesion.estado == EstadoCajaEnum.ABIERTA).first()
    if datos.metodo_pago == MetodoPagoEnum.EFECTIVO and not caja:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede registrar un cobro en efectivo si no hay una caja abierta"
        )
    if datos.es_cobro_directo:
        validar_cobro_directo(datos.paciente_id, datos.plan_id, datos.observaciones, db)
    else:
        validar_monto_cobro(datos.paciente_id, datos.plan_id, datos.monto, db)
    if datos.doctor_comision_id and not db.query(Doctor.id).filter(Doctor.id == datos.doctor_comision_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor no encontrado")

    nuevo_pago = Pago(
        **datos.model_dump(),
        porcentaje_comision=porcentaje_vigente(datos.doctor_comision_id, db),
        caja_sesion_id=caja.id if caja else None,
        registrado_por_usuario_id=current_user.id
    )
    db.add(nuevo_pago)

    # Si fue en efectivo y hay caja abierta, sumar a ingresos en efectivo
    if datos.metodo_pago == MetodoPagoEnum.EFECTIVO and caja:
        caja.total_ingresos_efectivo += datos.monto
        caja.saldo_efectivo_esperado = caja.monto_inicial_fondo + caja.total_ingresos_efectivo - caja.total_egresos_efectivo

    db.flush()

    log = AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="pagos",
        registro_id=nuevo_pago.id,
        accion=AuditoriaAccionEnum.INSERT,
        seccion_consultada="REGISTRO_PAGO"
    )
    db.add(log)
    db.commit()
    db.refresh(nuevo_pago)
    return nuevo_pago

@router.post("/pagos/{id}/anular", response_model=PagoResponse)
def anular_pago_paciente(
    id: UUID,
    datos: PagoAnular,
    current_user: Usuario = Depends(require_permission("CAJA_ANULAR_PAGOS")),
    db: Session = Depends(get_db)
):
    """Anula el pago sin borrarlo: revierte la caja, devuelve la deuda y conserva el registro y su motivo."""
    # El bloqueo evita que dos usuarios anulen el mismo pago y devuelvan el dinero dos veces
    pago = db.query(Pago).filter(Pago.id == id).with_for_update().first()
    if not pago:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pago no encontrado")
    anular_pago(pago, datos.motivo, current_user.id, db)
    db.commit()
    db.refresh(pago)
    return pago

def crear_egreso(datos: EgresoCajaCreate, current_user: Usuario, db: Session) -> EgresoCaja:
    """Descuenta el efectivo de la gaveta y deja el registro. Quien llama confirma la transacción."""
    caja = db.query(CajaSesion).filter(CajaSesion.estado == EstadoCajaEnum.ABIERTA).with_for_update().first()
    if not caja:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede registrar un egreso de efectivo si no hay una caja abierta"
        )
    exigir_efectivo(caja, datos.monto, "retirar")

    nuevo_egreso = EgresoCaja(
        **datos.model_dump(),
        caja_sesion_id=caja.id,
        usuario_autoriza_id=current_user.id
    )
    db.add(nuevo_egreso)

    # Descontar del efectivo en gaveta
    caja.total_egresos_efectivo += datos.monto
    caja.saldo_efectivo_esperado = caja.monto_inicial_fondo + caja.total_ingresos_efectivo - caja.total_egresos_efectivo
    db.flush()

    log = AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="egresos_caja",
        registro_id=nuevo_egreso.id,
        accion=AuditoriaAccionEnum.INSERT,
        seccion_consultada="EGRESO_CAJA"
    )
    db.add(log)
    return nuevo_egreso


@router.post("/egresos", response_model=EgresoCajaResponse, status_code=status.HTTP_201_CREATED)
def registrar_egreso_caja(
    datos: EgresoCajaCreate,
    current_user: Usuario = Depends(require_permission("CAJA_EGRESOS")),
    db: Session = Depends(get_db)
):
    """
    Registra salida física de efectivo: adelanto de sueldo, comisiones, compra de insumos urgentes o pago a laboratorio.
    """
    nuevo_egreso = crear_egreso(datos, current_user, db)
    db.commit()
    db.refresh(nuevo_egreso)
    return nuevo_egreso
