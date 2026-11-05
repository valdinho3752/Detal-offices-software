from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import Usuario, RolCodigoEnum

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(
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
    except JWTError:
        raise credentials_exception

    user = db.query(Usuario).filter(Usuario.username == username).first()
    if user is None:
        raise credentials_exception
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Usuario inactivo en el sistema"
        )
    return user

def require_role(*roles_permitidos):
    """
    Verifica que el usuario actual pertenezca a uno de los roles autorizados.
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
