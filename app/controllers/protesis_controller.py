from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    OrdenLaboratorioProtesis, EstadoOrdenProtesisEnum, Usuario, Doctor, RolCodigoEnum,
    AuditoriaLog, AuditoriaAccionEnum
)
from app.core.dependencies import es_admin, require_permission
from app.controllers.caja_controller import crear_egreso
from app.models.enums import CategoriaEgresoCajaEnum
from app.schemas.caja import EgresoCajaCreate
from app.schemas.protesis import OrdenLaboratorioCreate, OrdenLaboratorioUpdate, OrdenLaboratorioResponse, PagoLaboratorio

router = APIRouter(prefix="/protesis", tags=["Órdenes de Laboratorio y Prótesis"])

@router.get("/", response_model=List[OrdenLaboratorioResponse])
def listar_ordenes_protesis(
    paciente_id: Optional[UUID] = None,
    doctor_id: Optional[UUID] = None,
    estado: Optional[EstadoOrdenProtesisEnum] = None,
    current_user: Usuario = Depends(require_permission("PROTESIS_READ")),
    db: Session = Depends(get_db)
):
    query = db.query(OrdenLaboratorioProtesis)
    if paciente_id:
        query = query.filter(OrdenLaboratorioProtesis.paciente_id == paciente_id)
    if doctor_id:
        query = query.filter(OrdenLaboratorioProtesis.doctor_id == doctor_id)
    if estado:
        query = query.filter(OrdenLaboratorioProtesis.estado == estado)

    return query.order_by(OrdenLaboratorioProtesis.fecha_entrega_esperada).all()

def _validar_fechas(envio, entrega) -> None:
    if envio and entrega and entrega < envio:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La entrega no puede ser anterior a la fecha de envío")

@router.post("/", response_model=OrdenLaboratorioResponse, status_code=status.HTTP_201_CREATED)
def crear_orden_protesis(
    datos: OrdenLaboratorioCreate,
    current_user: Usuario = Depends(require_permission("PROTESIS_CREATE")),
    db: Session = Depends(get_db)
):
    _validar_fechas(datos.fecha_envio, datos.fecha_entrega_esperada)
    doctor_obj = None
    if datos.doctor_id:
        doctor_obj = db.query(Doctor).filter(
            (Doctor.id == datos.doctor_id) | (Doctor.usuario_id == datos.doctor_id)
        ).first()

    puede_elegir_doctor = es_admin(current_user) or not current_user.doctor_perfil
    resolved_doctor_id = None
    if puede_elegir_doctor:
        if doctor_obj:
            resolved_doctor_id = doctor_obj.id
        elif current_user.doctor_perfil:
            resolved_doctor_id = current_user.doctor_perfil.id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debes especificar un doctor válido para la orden de prótesis"
            )
    else:
        resolved_doctor_id = current_user.doctor_perfil.id
        if doctor_obj and doctor_obj.id != current_user.doctor_perfil.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para asignar órdenes a otros doctores"
            )

    order_data = datos.model_dump()
    order_data["doctor_id"] = resolved_doctor_id
    nueva_orden = OrdenLaboratorioProtesis(**order_data)
    db.add(nueva_orden)
    db.flush()

    log = AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="ordenes_laboratorio_protesis",
        registro_id=nueva_orden.id,
        accion=AuditoriaAccionEnum.INSERT,
        seccion_consultada="ORDEN_LABORATORIO"
    )
    db.add(log)
    db.commit()
    db.refresh(nueva_orden)
    return nueva_orden

@router.put("/{id}", response_model=OrdenLaboratorioResponse)
def actualizar_orden_protesis(
    id: UUID,
    datos: OrdenLaboratorioUpdate,
    current_user: Usuario = Depends(require_permission("PROTESIS_UPDATE")),
    db: Session = Depends(get_db)
):
    orden = db.query(OrdenLaboratorioProtesis).filter(OrdenLaboratorioProtesis.id == id).first()
    if not orden:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden de prótesis no encontrada")

    update_dict = datos.model_dump(exclude_unset=True)
    if "doctor_id" in update_dict and update_dict["doctor_id"] is not None:
        target_doc = update_dict["doctor_id"]
        doctor_obj = db.query(Doctor).filter(
            (Doctor.id == target_doc) | (Doctor.usuario_id == target_doc)
        ).first()

        if es_admin(current_user) or not current_user.doctor_perfil:
            if not doctor_obj:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor no encontrado")
            update_dict["doctor_id"] = doctor_obj.id
        else:
            if doctor_obj and doctor_obj.id != current_user.doctor_perfil.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Solo administradores pueden reasignar órdenes de prótesis a otros doctores"
                )
            update_dict["doctor_id"] = current_user.doctor_perfil.id

    _validar_fechas(orden.fecha_envio, update_dict.get("fecha_entrega_esperada") or orden.fecha_entrega_esperada)

    for field, value in update_dict.items():
        setattr(orden, field, value)

    log = AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="ordenes_laboratorio_protesis",
        registro_id=orden.id,
        accion=AuditoriaAccionEnum.UPDATE,
        seccion_consultada="ORDEN_LABORATORIO"
    )
    db.add(log)
    db.commit()
    db.refresh(orden)
    return orden


@router.post("/{id}/pagar-laboratorio", response_model=OrdenLaboratorioResponse)
def pagar_laboratorio(
    id: UUID,
    datos: PagoLaboratorio,
    current_user: Usuario = Depends(require_permission("CAJA_EGRESOS")),
    db: Session = Depends(get_db),
):
    """Paga la orden desde la caja y la deja vinculada al egreso: así se sabe cuáles ya están pagadas."""
    # El bloqueo evita que dos clics simultáneos paguen dos veces la misma orden
    orden = db.query(OrdenLaboratorioProtesis).filter(OrdenLaboratorioProtesis.id == id).with_for_update().first()
    if not orden:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada")
    if orden.egreso_caja_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Esta orden ya está pagada")
    if orden.costo_laboratorio <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La orden no tiene costo de laboratorio")
    egreso = crear_egreso(EgresoCajaCreate(
        categoria=CategoriaEgresoCajaEnum.PAGO_LABORATORIO_PROTESIS,
        monto=orden.costo_laboratorio,
        concepto_motivo=f"Laboratorio {orden.laboratorio_nombre}"[:255],
        numero_recibo_comprobante=datos.numero_recibo_comprobante,
    ), current_user, db)
    db.flush()
    orden.egreso_caja_id = egreso.id
    db.add(AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="ordenes_laboratorio_protesis",
        registro_id=orden.id,
        accion=AuditoriaAccionEnum.UPDATE,
        seccion_consultada="ORDEN_LABORATORIO_PAGADA",
        datos_nuevos={"egreso_caja_id": str(egreso.id), "monto": float(orden.costo_laboratorio)},
    ))
    db.commit()
    db.refresh(orden)
    return orden
