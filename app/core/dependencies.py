from typing import Optional, Set
from uuid import UUID
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt import PyJWTError
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import Usuario, Doctor, Permiso

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Lo único disponible hasta cambiar una contraseña que otra persona conoce
RUTAS_SIN_CAMBIO_DE_CONTRASENA = ("/auth/me", "/auth/cambiar-contrasena", "/configuracion/")

def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales de autenticación",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception

    user = db.query(Usuario).filter(Usuario.username == username).first()
    if user is None:
        raise credentials_exception
    # Tras cambiar la contraseña, las sesiones emitidas antes dejan de servir
    if payload.get("sv", 0) != user.version_sesion:
        raise credentials_exception
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo en el sistema"
        )
    if settings.es_produccion and user.debe_cambiar_contrasena and not request.url.path.endswith(RUTAS_SIN_CAMBIO_DE_CONTRASENA):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debes cambiar tu contraseña antes de continuar"
        )
    return user

def es_admin(usuario: Usuario) -> bool:
    return bool(usuario.rol) and str(usuario.rol.codigo).upper() == "ADMIN"

def permisos_efectivos(usuario: Usuario, db: Session) -> Set[str]:
    """
    Permisos vigentes del usuario: los de su rol más sus excepciones individuales.
    Se calculan en cada petición, así que un cambio de permisos aplica de inmediato.
    El rol ADMIN tiene todos.
    """
    if es_admin(usuario):
        return {codigo for (codigo,) in db.query(Permiso.codigo_permiso).all()}

    permisos = {rp.permiso.codigo_permiso for rp in usuario.rol.permisos_asociados} if usuario.rol else set()
    for especial in usuario.permisos_especiales:
        if especial.concedido:
            permisos.add(especial.permiso.codigo_permiso)
        else:
            permisos.discard(especial.permiso.codigo_permiso)
    return permisos

def tiene_permiso(usuario: Usuario, codigo: str, db: Session) -> bool:
    return es_admin(usuario) or codigo in permisos_efectivos(usuario, db)

def require_permission(*codigos: str):
    """Exige al menos uno de los permisos indicados. Funciona igual para roles personalizados."""
    def verificador(
        current_user: Usuario = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> Usuario:
        if es_admin(current_user) or permisos_efectivos(current_user, db).intersection(codigos):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acceso denegado: necesitas el permiso {' o '.join(codigos)}"
        )
    return verificador

def require_role(*roles_permitidos):
    """
    Verifica que el usuario actual pertenezca a uno de los roles autorizados.
    Solo para acciones reservadas a un rol concreto; lo demás usa require_permission.
    El rol ADMIN tiene pase libre general.
    """
    codigos_permitidos = [
        r.value if hasattr(r, "value") else str(r).upper()
        for r in roles_permitidos
    ]
    def role_checker(current_user: Usuario = Depends(get_current_user)) -> Usuario:
        rol_actual = str(current_user.rol.codigo).upper()
        if rol_actual == "ADMIN":
            return current_user
        if rol_actual not in codigos_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado: se requiere uno de los roles {codigos_permitidos}"
            )
        return current_user
    return role_checker

def doctor_solicitado(doctor_id: Optional[UUID], db: Session) -> Doctor:
    """
    Doctor responsable cuando quien registra no tiene perfil médico propio,
    como un rol personalizado con permisos clínicos: debe indicar a qué doctor corresponde.
    """
    doctor = None
    if doctor_id:
        doctor = db.query(Doctor).filter((Doctor.id == doctor_id) | (Doctor.usuario_id == doctor_id)).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes indicar el doctor responsable de este registro"
        )
    return doctor
