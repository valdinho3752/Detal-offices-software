import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import jwt
from app.config import settings

def hash_password(password: str) -> str:
    """Hashea una contraseña usando bcrypt nativo."""
    # Truncar a 72 bytes por limitación de diseño de bcrypt
    pwd_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña en texto plano coincide con el hash almacenado."""
    try:
        pwd_bytes = plain_password.encode('utf-8')[:72]
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False

def emitir_token_de(usuario) -> str:
    rol = usuario.rol.codigo.value if hasattr(usuario.rol.codigo, "value") else str(usuario.rol.codigo)
    return create_access_token(data={"sub": usuario.username, "rol": rol, "user_id": str(usuario.id), "sv": usuario.version_sesion})

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Genera un token JWT firmado."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
