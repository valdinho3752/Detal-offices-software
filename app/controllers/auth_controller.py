from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AuditoriaAccionEnum, AuditoriaLog, Usuario, RegistroAsistencia, Rol
from app.core.limite_login import limite_login
from app.core.security import emitir_token_de, hash_password, verify_password
from app.core.dependencies import get_current_user, permisos_efectivos, require_permission
from app.schemas.auth import CambioContrasena, Token, UsuarioSimpleResponse
from app.schemas.asistencia import AsistenciaCreate, AsistenciaResponse, EstadoTurnoResponse
from app.services.asistencia import consultar_estado

router = APIRouter(prefix="/auth", tags=["Autenticación y Asistencia"])

@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Inicia sesión con username y password, devolviendo un Bearer Token JWT.
    """
    equipo = request.client.host if request.client else "desconocido"
    limite_login.exigir_permitido(form_data.username, equipo)

    user = db.query(Usuario).filter(Usuario.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        limite_login.registrar_fallo(form_data.username, equipo)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas: usuario o contraseña no válidos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este usuario se encuentra inactivo",
        )
    
    limite_login.registrar_exito(form_data.username, equipo)
    return {"access_token": emitir_token_de(user), "token_type": "bearer"}

@router.post("/cambiar-contrasena", response_model=Token)
def cambiar_contrasena_propia(
    datos: CambioContrasena,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(datos.actual, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La contraseña actual no es correcta")
    if datos.nueva == datos.actual:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La contraseña nueva debe ser distinta de la actual")

    current_user.password_hash = hash_password(datos.nueva)
    current_user.debe_cambiar_contrasena = False
    # Cierra las demás sesiones; esta continúa con el token nuevo
    current_user.version_sesion += 1
    db.add(AuditoriaLog(
        usuario_id=current_user.id,
        tabla_afectada="usuarios",
        registro_id=current_user.id,
        accion=AuditoriaAccionEnum.UPDATE,
        seccion_consultada="CAMBIO_CONTRASENA",
    ))
    db.commit()
    db.refresh(current_user)
    return {"access_token": emitir_token_de(current_user), "token_type": "bearer"}

@router.get("/me", response_model=UsuarioSimpleResponse)
def get_me(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Devuelve los datos del usuario autenticado en la sesión actual.
    """
    rol_codigo = current_user.rol.codigo.value if hasattr(current_user.rol.codigo, "value") else str(current_user.rol.codigo)
    doc_id = current_user.doctor_perfil.id if current_user.doctor_perfil else None
    return UsuarioSimpleResponse(
        id=current_user.id,
        username=current_user.username,
        nombre=current_user.nombre,
        apellido=current_user.apellido,
        email=current_user.email,
        telefono=current_user.telefono,
        rol=rol_codigo,
        rol_nombre=current_user.rol.nombre,
        activo=current_user.activo,
        doctor_id=doc_id,
        permisos=sorted(permisos_efectivos(current_user, db)),
        debe_cambiar_contrasena=current_user.debe_cambiar_contrasena,
    )

@router.get("/fichaje/estado", response_model=EstadoTurnoResponse)
def consultar_estado_de_turno(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Qué marcajes puede hacer ahora la persona conectada."""
    turno = consultar_estado(current_user.id, db)
    return EstadoTurnoResponse(
        estado=turno.estado,
        permitidos=list(turno.permitidos),
        desde=turno.desde,
        jornada_sin_salida=turno.jornada_sin_salida,
    )

@router.post("/fichar", response_model=AsistenciaResponse)
def registrar_asistencia(
    datos: AsistenciaCreate,
    request: Request,
    current_user: Usuario = Depends(require_permission("ASISTENCIA_FICHAR")),
    db: Session = Depends(get_db)
):
    """
    Fichaje laboral: Registra hora de entrada, salida o descanso de doctores y asistentes.
    Cada marcaje solo es válido según el anterior de la misma persona.
    """
    # El bloqueo evita que dos marcajes simultáneos pasen la misma validación
    db.query(Usuario).filter(Usuario.id == current_user.id).with_for_update(of=Usuario).first()
    turno = consultar_estado(current_user.id, db)
    if datos.tipo_evento not in turno.permitidos:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=turno.motivo_bloqueo)

    client_ip = request.client.host if request.client else None
    
    registro = RegistroAsistencia(
        usuario_id=current_user.id,
        tipo_evento=datos.tipo_evento,
        observaciones=datos.observaciones,
        ip_registro=client_ip
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro
