from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import RadiografiaEstudio, Usuario, AuditoriaLog, AuditoriaAccionEnum
from app.core.dependencies import require_permission
from app.schemas.radiografia import (
    RadiografiaCreate, RadiografiaUpdate, RadiografiaResponse
)

router = APIRouter(prefix="/radiografias", tags=["Radiografías e Imágenes Dentales"])

@router.get("/", response_model=List[RadiografiaResponse])
def listar_radiografias(
    paciente_id: UUID,
    pieza_fdi: Optional[int] = None,
    current_user: Usuario = Depends(require_permission("RADIOGRAFIAS_READ")),
    db: Session = Depends(get_db)
):
    query = db.query(RadiografiaEstudio).filter(RadiografiaEstudio.paciente_id == paciente_id)
    if pieza_fdi:
        query = query.filter(RadiografiaEstudio.pieza_fdi == pieza_fdi)
    return query.order_by(RadiografiaEstudio.fecha_toma.desc()).all()

@router.post("/", response_model=RadiografiaResponse, status_code=status.HTTP_201_CREATED)
def registrar_radiografia(
    datos: RadiografiaCreate,
    current_user: Usuario = Depends(require_permission("RADIOGRAFIAS_CREATE")),
    db: Session = Depends(get_db)
):
    estudio = RadiografiaEstudio(
        **datos.model_dump(),
        subido_por_usuario_id=current_user.id
    )
    db.add(estudio)
    db.flush()

    # Log de auditoría de subida de imagen médica
    log = AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="radiografias_estudios",
        registro_id=estudio.id,
        accion=AuditoriaAccionEnum.INSERT,
        seccion_consultada="SUBIDA_ESTUDIO_IMAGEN"
    )
    db.add(log)
    db.commit()
    db.refresh(estudio)
    return estudio

@router.get("/{id}", response_model=RadiografiaResponse)
def obtener_radiografia(
    id: UUID,
    request: Request,
    current_user: Usuario = Depends(require_permission("RADIOGRAFIAS_READ")),
    db: Session = Depends(get_db)
):
    estudio = db.query(RadiografiaEstudio).filter(RadiografiaEstudio.id == id).first()
    if not estudio:
        raise HTTPException(status_code=404, detail="Estudio radiológico no encontrado")

    # Auditoría VIEW
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    log = AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="radiografias_estudios",
        registro_id=estudio.id,
        accion=AuditoriaAccionEnum.VIEW,
        seccion_consultada="VISOR_RADIOGRAFIA",
        ip_origen=client_ip,
        user_agent=user_agent
    )
    db.add(log)
    db.commit()

    return estudio

@router.put("/{id}", response_model=RadiografiaResponse)
def actualizar_radiografia(
    id: UUID,
    datos: RadiografiaUpdate,
    current_user: Usuario = Depends(require_permission("RADIOGRAFIAS_CREATE")),
    db: Session = Depends(get_db)
):
    estudio = db.query(RadiografiaEstudio).filter(RadiografiaEstudio.id == id).first()
    if not estudio:
        raise HTTPException(status_code=404, detail="Estudio radiológico no encontrado")
    for field, value in datos.model_dump(exclude_unset=True).items():
        setattr(estudio, field, value)
    db.commit()
    db.refresh(estudio)
    return estudio

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_radiografia(
    id: UUID,
    current_user: Usuario = Depends(require_permission("RADIOGRAFIAS_DELETE")),
    db: Session = Depends(get_db)
):
    estudio = db.query(RadiografiaEstudio).filter(RadiografiaEstudio.id == id).first()
    if not estudio:
        raise HTTPException(status_code=404, detail="Estudio radiológico no encontrado")
    db.delete(estudio)
    db.commit()
    return None
