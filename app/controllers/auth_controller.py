from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Usuario, RegistroAsistencia, Rol
from app.core.security import verify_password, create_access_token
from app.core.dependencies import get_current_user, permisos_efectivos, require_permission
from app.schemas.auth import Token, UsuarioSimpleResponse
from app.schemas.asistencia import AsistenciaCreate, AsistenciaResponse

router = APIRouter(prefix="/auth", tags=["Autenticación y Asistencia"])

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Inicia sesión con username y password, devolviendo un Bearer Token JWT.
    """
    user = db.query(Usuario).filter(Usuario.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
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
    
    rol_codigo = user.rol.codigo.value if hasattr(user.rol.codigo, "value") else str(user.rol.codigo)
    access_token = create_access_token(
        data={"sub": user.username, "rol": rol_codigo, "user_id": str(user.id)}
    )
    return {"access_token": access_token, "token_type": "bearer"}

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
        permisos=sorted(permisos_efectivos(current_user, db))
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
    """
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
