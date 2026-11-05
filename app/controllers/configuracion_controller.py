from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_role
from app.database import get_db
from app.models import AuditoriaAccionEnum, AuditoriaLog, RolCodigoEnum, Usuario
from app.schemas.configuracion import ConfiguracionActualizar, ConfiguracionRespuesta
from app.services.moneda import obtener_configuracion

router = APIRouter(prefix="/configuracion", tags=["Configuración de la Clínica"])


@router.get("/", response_model=ConfiguracionRespuesta)
def consultar_configuracion(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return obtener_configuracion(db)


@router.put("/", response_model=ConfiguracionRespuesta)
def actualizar_configuracion(
    datos: ConfiguracionActualizar,
    current_user: Usuario = Depends(require_role(RolCodigoEnum.ADMIN)),
    db: Session = Depends(get_db)
):
    configuracion = obtener_configuracion(db)
    previo = configuracion.moneda_simbolo
    if previo != datos.moneda_simbolo:
        configuracion.moneda_simbolo = datos.moneda_simbolo
        db.add(AuditoriaLog(
            usuario_id=current_user.id,
            tabla_afectada="configuracion_clinica",
            accion=AuditoriaAccionEnum.UPDATE,
            seccion_consultada="CONFIGURACION_MONEDA",
            datos_previos={"moneda_simbolo": previo},
            datos_nuevos={"moneda_simbolo": datos.moneda_simbolo},
        ))
    db.commit()
    db.refresh(configuracion)
    return configuracion
