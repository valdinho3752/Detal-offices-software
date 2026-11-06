from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_role
from app.database import get_db
from app.config import settings
from app.models import AuditoriaAccionEnum, AuditoriaLog, ConfiguracionClinica, EstadoCopias, RolCodigoEnum, Usuario
from app.schemas.configuracion import ConfiguracionActualizar, ConfiguracionPublica, ConfiguracionRespuesta
from app.services.moneda import obtener_configuracion

router = APIRouter(prefix="/configuracion", tags=["Configuración de la Clínica"])

LOGO_TAMANO_MAXIMO = 1024 * 1024
# Se identifica por su contenido. SVG queda fuera porque puede ejecutar código en el navegador.
FIRMAS_LOGO = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
)


def _tipo_de_imagen(contenido: bytes) -> Optional[str]:
    for firma, tipo in FIRMAS_LOGO:
        if contenido.startswith(firma):
            return tipo
    if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "image/webp"
    return None


def _logo_url(configuracion: ConfiguracionClinica) -> Optional[str]:
    if not configuracion.logo:
        return None
    # La versión sale del contenido: el navegador puede guardarlo sin mostrar nunca uno viejo
    return f"/api/v1/configuracion/logo?v={sha256(bytes(configuracion.logo)).hexdigest()[:16]}"


def _publica(configuracion: ConfiguracionClinica) -> dict:
    return {
        "nombre_clinica": configuracion.nombre_clinica,
        "tema_por_defecto": configuracion.tema_por_defecto,
        "logo_url": _logo_url(configuracion),
        "zona_horaria": settings.CLINICA_TIMEZONE or None,
    }


def _completa(configuracion: ConfiguracionClinica) -> dict:
    return {
        **_publica(configuracion),
        "moneda_simbolo": configuracion.moneda_simbolo,
        "meses_inactividad_paciente": configuracion.meses_inactividad_paciente,
    }


def _auditar(usuario: Usuario, seccion: str, previos: dict, nuevos: dict) -> AuditoriaLog:
    return AuditoriaLog(
        usuario_id=usuario.id,
        tabla_afectada="configuracion_clinica",
        accion=AuditoriaAccionEnum.UPDATE,
        seccion_consultada=seccion,
        datos_previos=previos,
        datos_nuevos=nuevos,
    )


@router.get("/publica", response_model=ConfiguracionPublica)
def consultar_configuracion_publica(db: Session = Depends(get_db)):
    configuracion = obtener_configuracion(db)
    db.commit()
    return _publica(configuracion)


HORAS_SIN_COPIA_PARA_AVISAR = 26  # Una copia diaria, con margen para el horario de trabajo


@router.get("/estado-copias")
def consultar_estado_copias(
    current_user: Usuario = Depends(require_role(RolCodigoEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    estado = db.query(EstadoCopias).first()
    if not estado:
        return {"alerta": False, "mensaje": None}
    if estado.ultimo_error_en and (not estado.ultima_exitosa or estado.ultimo_error_en > estado.ultima_exitosa):
        return {"alerta": True, "mensaje": f"La copia de seguridad falló el {estado.ultimo_error_en:%d/%m/%Y %H:%M}. Revisa el disco de copias: sin copia no se pueden recuperar los datos."}
    referencia = estado.ultima_exitosa or estado.creado_en
    if datetime.now(timezone.utc) - referencia > timedelta(hours=HORAS_SIN_COPIA_PARA_AVISAR):
        ultima = f"desde el {estado.ultima_exitosa:%d/%m/%Y %H:%M}" if estado.ultima_exitosa else "todavía"
        return {"alerta": True, "mensaje": f"No se ha creado ninguna copia de seguridad {ultima}. Revisa que el servicio de copias esté en marcha."}
    return {"alerta": False, "mensaje": None}


@router.get("/logo", response_class=Response)
def consultar_logo(db: Session = Depends(get_db)):
    configuracion = obtener_configuracion(db)
    if not configuracion.logo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La clínica no tiene logo")
    return Response(
        content=bytes(configuracion.logo),
        media_type=configuracion.logo_tipo,
        headers={"Cache-Control": "public, max-age=31536000, immutable", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/logo", response_model=ConfiguracionRespuesta)
async def actualizar_logo(
    archivo: UploadFile = File(...),
    current_user: Usuario = Depends(require_role(RolCodigoEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    contenido = await archivo.read(LOGO_TAMANO_MAXIMO + 1)
    if len(contenido) > LOGO_TAMANO_MAXIMO:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="El logo no puede superar 1 MB")
    tipo = _tipo_de_imagen(contenido)
    if not tipo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El logo debe ser una imagen PNG, JPG o WEBP")

    configuracion = obtener_configuracion(db)
    previo = {"logo": bool(configuracion.logo)}
    configuracion.logo = contenido
    configuracion.logo_tipo = tipo
    db.add(_auditar(current_user, "CONFIGURACION_LOGO", previo, {"logo": True, "tipo": tipo, "bytes": len(contenido)}))
    db.commit()
    db.refresh(configuracion)
    return _completa(configuracion)


@router.delete("/logo", response_model=ConfiguracionRespuesta)
def eliminar_logo(
    current_user: Usuario = Depends(require_role(RolCodigoEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    configuracion = obtener_configuracion(db)
    if configuracion.logo:
        configuracion.logo = None
        configuracion.logo_tipo = None
        db.add(_auditar(current_user, "CONFIGURACION_LOGO", {"logo": True}, {"logo": False}))
        db.commit()
        db.refresh(configuracion)
    return _completa(configuracion)


@router.get("/", response_model=ConfiguracionRespuesta)
def consultar_configuracion(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    configuracion = obtener_configuracion(db)
    db.commit()
    return _completa(configuracion)


@router.put("/", response_model=ConfiguracionRespuesta)
def actualizar_configuracion(
    datos: ConfiguracionActualizar,
    current_user: Usuario = Depends(require_role(RolCodigoEnum.ADMIN)),
    db: Session = Depends(get_db)
):
    configuracion = obtener_configuracion(db)
    cambios = {
        campo: valor for campo, valor in datos.model_dump(exclude_unset=True).items()
        if getattr(configuracion, campo) != valor
    }
    if cambios:
        previos = {campo: getattr(configuracion, campo) for campo in cambios}
        for campo, valor in cambios.items():
            setattr(configuracion, campo, valor)
        db.add(_auditar(current_user, "CONFIGURACION_CLINICA", previos, cambios))
    db.commit()
    db.refresh(configuracion)
    return _completa(configuracion)
