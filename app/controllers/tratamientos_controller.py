from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import (
    CatalogoTratamiento, PlanTratamiento, ItemPlanTratamiento,
    Usuario, AuditoriaLog, AuditoriaAccionEnum, Doctor
)
from app.core.dependencies import get_current_user
from app.schemas.tratamiento import (
    CatalogoTratamientoCreate, CatalogoTratamientoUpdate, CatalogoTratamientoResponse,
    PlanTratamientoCreate, PlanTratamientoUpdate, PlanTratamientoResponse,
    ItemPlanTratamientoCreate, ItemPlanTratamientoUpdate, ItemPlanTratamientoResponse
)

router = APIRouter(prefix="/tratamientos", tags=["Catálogo y Planes de Tratamiento"])

# ==================== CATÁLOGO DE TRATAMIENTOS ====================

@router.get("/catalogo", response_model=List[CatalogoTratamientoResponse])
def listar_catalogo(
    activo_solo: bool = True,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(CatalogoTratamiento)
    if activo_solo:
        query = query.filter(CatalogoTratamiento.activo == True)
    return query.order_by(CatalogoTratamiento.categoria, CatalogoTratamiento.nombre).all()

@router.post("/catalogo", response_model=CatalogoTratamientoResponse, status_code=status.HTTP_201_CREATED)
def crear_tratamiento_catalogo(
    datos: CatalogoTratamientoCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if db.query(CatalogoTratamiento).filter(CatalogoTratamiento.codigo == datos.codigo).first():
        raise HTTPException(status_code=400, detail="El código de tratamiento ya existe")
    item = CatalogoTratamiento(**datos.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.put("/catalogo/{id}", response_model=CatalogoTratamientoResponse)
def actualizar_tratamiento_catalogo(
    id: UUID,
    datos: CatalogoTratamientoUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item = db.query(CatalogoTratamiento).filter(CatalogoTratamiento.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Tratamiento de catálogo no encontrado")
    for field, value in datos.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item

# ==================== PLANES DE TRATAMIENTO ====================

@router.get("/planes", response_model=List[PlanTratamientoResponse])
def listar_planes(
    paciente_id: Optional[UUID] = None,
    doctor_id: Optional[UUID] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(PlanTratamiento)
    if paciente_id:
        query = query.filter(PlanTratamiento.paciente_id == paciente_id)
    if doctor_id:
        query = query.filter(PlanTratamiento.doctor_id == doctor_id)
    return query.order_by(PlanTratamiento.fecha_creacion.desc()).all()

@router.post("/planes", response_model=PlanTratamientoResponse, status_code=status.HTTP_201_CREATED)
def crear_plan_tratamiento(
    datos: PlanTratamientoCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    plan_dict = datos.model_dump(exclude={"items"})
    if not plan_dict.get("titulo"):
        plan_dict["titulo"] = plan_dict.get("nombre") or "Plan de Tratamiento Integral"
    plan_dict.pop("nombre", None)

    es_admin = current_user.rol and str(current_user.rol.codigo).upper() == "ADMIN"
    doctor = None

    if es_admin:
        if plan_dict.get("doctor_id"):
            doctor = db.query(Doctor).filter((Doctor.id == plan_dict["doctor_id"]) | (Doctor.usuario_id == plan_dict["doctor_id"])).first()
        if not doctor and current_user.doctor_perfil:
            doctor = current_user.doctor_perfil
        if not doctor:
            doctor = db.query(Doctor).first()
        if not doctor:
            doctor = Doctor(usuario_id=current_user.id, especialidad="Odontología General / Dirección Médica")
            db.add(doctor)
            db.flush()
    else:
        if not current_user.doctor_perfil:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: solo personal médico o administradores pueden formular planes de tratamiento"
            )
        doctor = current_user.doctor_perfil

    plan_dict["doctor_id"] = doctor.id
    nuevo_plan = PlanTratamiento(**plan_dict)
    db.add(nuevo_plan)
    db.flush()

    total = 0.0
    if datos.items:
        items_db = []
        valid_cols = {
            "plan_id", "tratamiento_id", "hallazgo_superficie_id", "pieza_fdi",
            "orden_secuencia", "fecha_programada", "estado", "costo_acordado", "observaciones"
        }
        for idx, it in enumerate(datos.items, start=1):
            it_dict = it.model_dump()
            it_dict["plan_id"] = nuevo_plan.id
            it_dict["orden_secuencia"] = it_dict.get("orden_secuencia") or idx
            filtered_it = {k: v for k, v in it_dict.items() if k in valid_cols}
            items_db.append(ItemPlanTratamiento(**filtered_it))
            total += float(it.costo_acordado or 0)
        db.add_all(items_db)
        nuevo_plan.costo_total = total

    db.commit()
    db.refresh(nuevo_plan)
    return nuevo_plan

@router.get("/planes/{id}", response_model=PlanTratamientoResponse)
def obtener_plan_tratamiento(
    id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    plan = db.query(PlanTratamiento).filter(PlanTratamiento.id == id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan de tratamiento no encontrado")
    return plan

@router.put("/planes/{id}", response_model=PlanTratamientoResponse)
def actualizar_plan_tratamiento(
    id: UUID,
    datos: PlanTratamientoUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    plan = db.query(PlanTratamiento).filter(PlanTratamiento.id == id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan de tratamiento no encontrado")

    update_data = datos.model_dump(exclude_unset=True)
    es_admin = current_user.rol and str(current_user.rol.codigo).upper() == "ADMIN"

    if "doctor_id" in update_data and update_data["doctor_id"]:
        if not es_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores pueden reasignar el doctor del plan de tratamiento"
            )
        doc = db.query(Doctor).filter((Doctor.id == update_data["doctor_id"]) | (Doctor.usuario_id == update_data["doctor_id"])).first()
        if doc:
            update_data["doctor_id"] = doc.id

    if "nombre" in update_data and not update_data.get("titulo"):
        update_data["titulo"] = update_data.pop("nombre")
    else:
        update_data.pop("nombre", None)

    for field, value in update_data.items():
        setattr(plan, field, value)
    db.commit()
    db.refresh(plan)
    return plan

# ==================== ITEMS / PASOS DEL PLAN ====================

@router.post("/items", response_model=ItemPlanTratamientoResponse, status_code=status.HTTP_201_CREATED)
def agregar_item_a_plan(
    datos: ItemPlanTratamientoCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    plan = db.query(PlanTratamiento).filter(PlanTratamiento.id == datos.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")

    item_data = datos.model_dump()
    if item_data.get("superficie") and not item_data.get("observaciones"):
        item_data["observaciones"] = f"Superficie: {item_data['superficie']}"

    valid_cols = {
        "plan_id", "tratamiento_id", "hallazgo_superficie_id", "pieza_fdi",
        "orden_secuencia", "fecha_programada", "estado", "costo_acordado", "observaciones"
    }
    filtered_data = {k: v for k, v in item_data.items() if k in valid_cols}

    item = ItemPlanTratamiento(**filtered_data)
    db.add(item)
    db.flush()

    # Recalcular costo total del plan
    plan.costo_total = db.query(func.coalesce(func.sum(ItemPlanTratamiento.costo_acordado), 0)).filter(
        ItemPlanTratamiento.plan_id == plan.id
    ).scalar()

    db.commit()
    db.refresh(item)
    return item

@router.put("/items/{id}", response_model=ItemPlanTratamientoResponse)
def actualizar_item_plan(
    id: UUID,
    datos: ItemPlanTratamientoUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item = db.query(ItemPlanTratamiento).filter(ItemPlanTratamiento.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Ítem de tratamiento no encontrado")

    update_dict = datos.model_dump(exclude_unset=True)
    if update_dict.get("superficie") and not update_dict.get("observaciones"):
        update_dict["observaciones"] = f"Superficie: {update_dict['superficie']}"

    valid_cols = {
        "tratamiento_id", "hallazgo_superficie_id", "pieza_fdi",
        "orden_secuencia", "fecha_programada", "estado", "costo_acordado", "observaciones"
    }
    filtered_data = {k: v for k, v in update_dict.items() if k in valid_cols}

    for field, value in filtered_data.items():
        setattr(item, field, value)

    db.flush()
    # Recalcular costo total del plan
    item.plan.costo_total = db.query(func.coalesce(func.sum(ItemPlanTratamiento.costo_acordado), 0)).filter(
        ItemPlanTratamiento.plan_id == item.plan_id
    ).scalar()

    db.commit()
    db.refresh(item)
    return item

@router.delete("/items/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_item_plan(
    id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item = db.query(ItemPlanTratamiento).filter(ItemPlanTratamiento.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Ítem de tratamiento no encontrado")
    plan = item.plan
    db.delete(item)
    db.flush()

    plan.costo_total = db.query(func.coalesce(func.sum(ItemPlanTratamiento.costo_acordado), 0)).filter(
        ItemPlanTratamiento.plan_id == plan.id
    ).scalar()

    db.commit()
    return None
