from datetime import datetime, timezone
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.dependencies import require_permission, require_role
from app.database import get_db
from app.models import AuditoriaAccionEnum, AuditoriaLog, Cita, EstadoCitaEnum, RolCodigoEnum, Sillon, Usuario
from app.schemas.sillon import SillonActualizar, SillonCrear, SillonRespuesta
from app.services.sillones import numero_sillon_de_notas

router = APIRouter(prefix="/sillones", tags=["Sillones"])

ESTADOS_SIN_RESERVA = (EstadoCitaEnum.CANCELADA, EstadoCitaEnum.NO_ASISTIO, EstadoCitaEnum.FINALIZADA)


def _datos(sillon: Sillon) -> dict:
    return {"numero": sillon.numero, "nombre": sillon.nombre, "especialidad": sillon.especialidad, "activo": sillon.activo}


def _auditar(usuario: Usuario, sillon: Sillon, accion, previos=None, nuevos=None) -> AuditoriaLog:
    return AuditoriaLog(
        usuario_id=usuario.id,
        tabla_afectada="sillones",
        registro_id=sillon.id,
        accion=accion,
        seccion_consultada="CONFIGURACION_SILLONES",
        datos_previos=previos,
        datos_nuevos=nuevos,
    )


def _validar_puede_retirarse(sillon: Sillon, db: Session) -> None:
    """La agenda necesita al menos un sillón, y un sillón con citas por atender no se puede quitar."""
    otros_activos = db.query(Sillon.id).filter(Sillon.activo.is_(True), Sillon.id != sillon.id).first()
    if not otros_activos:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debe quedar al menos un sillón activo")

    proximas = db.query(Cita.notas_adicionales).filter(
        Cita.estado.notin_(ESTADOS_SIN_RESERVA),
        Cita.fecha_fin_programada >= datetime.now(timezone.utc),
    ).all()
    cantidad = sum(1 for (notas,) in proximas if numero_sillon_de_notas(notas) == sillon.numero)
    if cantidad:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{sillon.nombre} tiene {cantidad} cita(s) por atender: cámbialas de sillón o cancélalas primero"
        )


def _obtener(id: UUID, db: Session) -> Sillon:
    sillon = db.query(Sillon).filter(Sillon.id == id).first()
    if not sillon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sillón no encontrado")
    return sillon


@router.get("/", response_model=List[SillonRespuesta])
def listar_sillones(
    current_user: Usuario = Depends(require_permission("CITAS_READ")),
    db: Session = Depends(get_db)
):
    return db.query(Sillon).order_by(Sillon.numero).all()


@router.post("/", response_model=SillonRespuesta, status_code=status.HTTP_201_CREATED)
def crear_sillon(
    datos: SillonCrear,
    current_user: Usuario = Depends(require_role(RolCodigoEnum.ADMIN)),
    db: Session = Depends(get_db)
):
    # Un número retirado no se reutiliza: las citas antiguas siguen apuntando a él
    numero = (db.query(func.max(Sillon.numero)).scalar() or 0) + 1
    sillon = Sillon(numero=numero, nombre=datos.nombre or f"Box {numero}", especialidad=datos.especialidad or None)
    db.add(sillon)
    db.flush()
    db.add(_auditar(current_user, sillon, AuditoriaAccionEnum.INSERT, nuevos=_datos(sillon)))
    db.commit()
    db.refresh(sillon)
    return sillon


@router.put("/{id}", response_model=SillonRespuesta)
def actualizar_sillon(
    id: UUID,
    datos: SillonActualizar,
    current_user: Usuario = Depends(require_role(RolCodigoEnum.ADMIN)),
    db: Session = Depends(get_db)
):
    sillon = _obtener(id, db)
    cambios = datos.model_dump(exclude_unset=True)
    if cambios.get("activo") is False and sillon.activo:
        _validar_puede_retirarse(sillon, db)

    previos = _datos(sillon)
    if cambios.get("nombre") is not None:
        sillon.nombre = cambios["nombre"]
    if "especialidad" in cambios:
        sillon.especialidad = cambios["especialidad"] or None
    if cambios.get("activo") is not None:
        sillon.activo = cambios["activo"]
    db.add(_auditar(current_user, sillon, AuditoriaAccionEnum.UPDATE, previos=previos, nuevos=_datos(sillon)))
    db.commit()
    db.refresh(sillon)
    return sillon


@router.delete("/{id}")
def eliminar_sillon(
    id: UUID,
    current_user: Usuario = Depends(require_role(RolCodigoEnum.ADMIN)),
    db: Session = Depends(get_db)
):
    """Un sillón con citas en su historial se desactiva, para que esas citas sigan identificadas."""
    sillon = _obtener(id, db)
    if sillon.activo:
        _validar_puede_retirarse(sillon, db)

    previos = _datos(sillon)
    historial = db.query(Cita.notas_adicionales).all()
    if any(numero_sillon_de_notas(notas) == sillon.numero for (notas,) in historial):
        sillon.activo = False
        db.add(_auditar(current_user, sillon, AuditoriaAccionEnum.UPDATE, previos=previos, nuevos=_datos(sillon)))
        db.commit()
        return {"resultado": "DESACTIVADO", "mensaje": f"{sillon.nombre} tiene citas en su historial: se desactivó y sale de la agenda."}

    db.add(_auditar(current_user, sillon, AuditoriaAccionEnum.DELETE, previos=previos))
    db.delete(sillon)
    db.commit()
    return {"resultado": "ELIMINADO", "mensaje": "Sillón eliminado."}
