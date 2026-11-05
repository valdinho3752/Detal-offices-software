from typing import List, Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import (
    CatalogoTratamiento, ItemPlanTratamiento, EstadoItemPlanEnum,
    Cita, EstadoCitaEnum, Doctor, Usuario, RolCodigoEnum,
    Pago, EgresoCaja, MetodoPagoEnum, CategoriaEgresoCajaEnum
)
from app.core.dependencies import require_permission
from app.schemas.reporte import (
    ReporteTratamientosDemandaResponse, TratamientoDemandaItem,
    ReporteProductividadDoctoresResponse, ProductividadDoctorItem,
    ResumenFinancieroResponse
)

router = APIRouter(prefix="/reportes", tags=["Reportes de Productividad y Business Intelligence"])

@router.get("/tratamientos-demanda", response_model=ReporteTratamientosDemandaResponse)
def reporte_tratamientos_mayor_demanda(
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    limit: int = 15,
    current_user: Usuario = Depends(require_permission("REPORTES_READ")),
    db: Session = Depends(get_db)
):
    """
    Ranking de procedimientos dentales más realizados y facturados en la clínica.
    """
    query = (
        db.query(
            CatalogoTratamiento.id.label("tratamiento_id"),
            CatalogoTratamiento.codigo.label("codigo"),
            CatalogoTratamiento.nombre.label("nombre"),
            CatalogoTratamiento.categoria.label("categoria"),
            func.count(ItemPlanTratamiento.id).label("cantidad_realizada"),
            func.coalesce(func.sum(ItemPlanTratamiento.costo_acordado), 0).label("facturacion_total")
        )
        .join(ItemPlanTratamiento, ItemPlanTratamiento.tratamiento_id == CatalogoTratamiento.id)
        .filter(ItemPlanTratamiento.estado == EstadoItemPlanEnum.COMPLETADO)
    )

    if fecha_desde:
        query = query.filter(ItemPlanTratamiento.created_at >= fecha_desde)
    if fecha_hasta:
        query = query.filter(ItemPlanTratamiento.created_at <= fecha_hasta)

    resultados = (
        query.group_by(CatalogoTratamiento.id)
        .order_by(
            func.count(ItemPlanTratamiento.id).desc(),
            func.sum(ItemPlanTratamiento.costo_acordado).desc()
        )
        .limit(limit)
        .all()
    )

    items = []
    total_completados = 0
    for r in resultados:
        items.append(
            TratamientoDemandaItem(
                tratamiento_id=r.tratamiento_id,
                codigo=r.codigo,
                nombre=r.nombre,
                categoria=str(r.categoria.value if hasattr(r.categoria, 'value') else r.categoria),
                cantidad_realizada=r.cantidad_realizada,
                facturacion_total=Decimal(str(r.facturacion_total))
            )
        )
        total_completados += r.cantidad_realizada

    return ReporteTratamientosDemandaResponse(
        total_procedimientos_completados=total_completados,
        ranking_tratamientos=items
    )

@router.get("/productividad-doctores", response_model=ReporteProductividadDoctoresResponse)
def reporte_productividad_sillon_doctores(
    doctor_id: Optional[UUID] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    current_user: Usuario = Depends(require_permission("REPORTES_READ")),
    db: Session = Depends(get_db)
):
    """
    Métricas de tiempo en sillón, ocupación de gabinete y tasas de inasistencia por profesional.
    """
    query_doctores = db.query(Doctor)
    if doctor_id:
        query_doctores = query_doctores.filter(Doctor.id == doctor_id)
    doctores = query_doctores.all()

    items = []
    gran_total_citas = 0

    for doc in doctores:
        citas_query = db.query(Cita).filter(Cita.doctor_id == doc.id)
        if fecha_desde:
            citas_query = citas_query.filter(Cita.fecha_inicio_programada >= fecha_desde)
        if fecha_hasta:
            citas_query = citas_query.filter(Cita.fecha_fin_programada <= fecha_hasta)

        total_citas = citas_query.count()
        finalizadas = citas_query.filter(Cita.estado == EstadoCitaEnum.FINALIZADA).count()
        no_asistio = citas_query.filter(Cita.estado == EstadoCitaEnum.NO_ASISTIO).count()
        canceladas = citas_query.filter(Cita.estado == EstadoCitaEnum.CANCELADA).count()

        tiempo_total_min = (
            citas_query.filter(Cita.estado == EstadoCitaEnum.FINALIZADA)
            .with_entities(func.coalesce(func.sum(Cita.duracion_sillon_minutos), 0))
            .scalar()
        )

        promedio_min = round(float(tiempo_total_min) / finalizadas, 1) if finalizadas > 0 else 0.0
        tasa_ausentismo = round((no_asistio / total_citas) * 100.0, 2) if total_citas > 0 else 0.0

        items.append(
            ProductividadDoctorItem(
                doctor_id=doc.id,
                doctor_nombre=f"{doc.usuario.nombre} {doc.usuario.apellido}",
                especialidad=doc.especialidad,
                total_citas=total_citas,
                citas_finalizadas=finalizadas,
                citas_no_asistio=no_asistio,
                citas_canceladas=canceladas,
                tasa_ausentismo_porcentaje=tasa_ausentismo,
                tiempo_total_sillon_minutos=int(tiempo_total_min),
                promedio_minutos_por_cita=promedio_min
            )
        )
        gran_total_citas += total_citas

    return ReporteProductividadDoctoresResponse(
        resumen_global_citas=gran_total_citas,
        doctores=items
    )

@router.get("/resumen-financiero", response_model=ResumenFinancieroResponse)
def reporte_resumen_financiero_global(
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    current_user: Usuario = Depends(require_permission("REPORTES_READ")),
    db: Session = Depends(get_db)
):
    """
    Balance financiero consolidado: ingresos por método de pago vs egresos operacionales.
    """
    # 1. Ingresos
    pagos_query = db.query(Pago.metodo_pago, func.coalesce(func.sum(Pago.monto), 0).label("subtotal"))
    if fecha_desde:
        pagos_query = pagos_query.filter(Pago.fecha_hora >= fecha_desde)
    if fecha_hasta:
        pagos_query = pagos_query.filter(Pago.fecha_hora <= fecha_hasta)
    ingresos_rows = pagos_query.group_by(Pago.metodo_pago).all()

    dict_ingresos = {m.value: Decimal("0.00") for m in MetodoPagoEnum}
    total_ingresos = Decimal("0.00")
    for metodo, subtotal in ingresos_rows:
        val = Decimal(str(subtotal))
        dict_ingresos[metodo.value] = val
        total_ingresos += val

    # 2. Egresos
    egresos_query = db.query(EgresoCaja.categoria, func.coalesce(func.sum(EgresoCaja.monto), 0).label("subtotal"))
    if fecha_desde:
        egresos_query = egresos_query.filter(EgresoCaja.fecha_hora >= fecha_desde)
    if fecha_hasta:
        egresos_query = egresos_query.filter(EgresoCaja.fecha_hora <= fecha_hasta)
    egresos_rows = egresos_query.group_by(EgresoCaja.categoria).all()

    dict_egresos = {c.value: Decimal("0.00") for c in CategoriaEgresoCajaEnum}
    total_egresos = Decimal("0.00")
    for cat, subtotal in egresos_rows:
        val = Decimal(str(subtotal))
        dict_egresos[cat.value] = val
        total_egresos += val

    balance_neto = total_ingresos - total_egresos

    return ResumenFinancieroResponse(
        total_ingresos=total_ingresos,
        ingresos_por_metodo=dict_ingresos,
        total_egresos=total_egresos,
        egresos_por_categoria=dict_egresos,
        balance_neto_operativo=balance_neto
    )
