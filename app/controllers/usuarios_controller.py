import re
import unicodedata
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Usuario, Rol, Permiso, RolPermiso, Doctor, Asistente
from app.core.security import hash_password
from app.core.dependencies import es_admin, get_current_user, permisos_efectivos, require_permission
from app.schemas.usuario import (
    UsuarioCreate, UsuarioUpdate, UsuarioDetailResponse,
    RolCreate, RolResponse, PermisoResponse,
    DoctorCreate, DoctorUpdate, DoctorResponse,
    AsistenteCreate, AsistenteUpdate, AsistenteResponse
)

router = APIRouter(prefix="/usuarios", tags=["Usuarios, Doctores y Roles"])

# ==================== ROLES Y PERMISOS ====================

@router.get("/roles", response_model=List[RolResponse])
def listar_roles(
    current_user: Usuario = Depends(require_permission("USUARIOS_MANAGE", "ROLES_MANAGE")),
    db: Session = Depends(get_db)
):
    return db.query(Rol).all()

def _codigo_desde_nombre(nombre: str) -> str:
    sin_acentos = "".join(c for c in unicodedata.normalize("NFKD", nombre) if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]+", "_", sin_acentos.upper()).strip("_")

def _permisos_validos(permiso_ids: List[UUID], current_user: Usuario, db: Session) -> None:
    """Quien no es administrador no puede otorgar un permiso que él mismo no tiene."""
    encontrados = db.query(Permiso).filter(Permiso.id.in_(permiso_ids)).all() if permiso_ids else []
    if len(encontrados) != len(set(permiso_ids)):
        raise HTTPException(status_code=400, detail="Alguno de los permisos indicados no existe")
    if es_admin(current_user):
        return
    propios = permisos_efectivos(current_user, db)
    ajenos = sorted(p.codigo_permiso for p in encontrados if p.codigo_permiso not in propios)
    if ajenos:
        raise HTTPException(status_code=403, detail=f"No puedes otorgar permisos que no tienes: {', '.join(ajenos)}")

def _validar_edicion_de_rol(rol_codigo: str, rol_id: UUID, current_user: Usuario) -> None:
    if es_admin(current_user):
        return
    if rol_codigo.upper() == "ADMIN" or rol_id == current_user.rol_id:
        raise HTTPException(status_code=403, detail="No puedes modificar el rol de administrador ni tu propio rol")

def _validar_rol_asignable(rol_id: UUID, current_user: Usuario, db: Session) -> None:
    rol = db.query(Rol).filter(Rol.id == rol_id).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    if str(rol.codigo).upper() == "ADMIN" and not es_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo un administrador puede asignar el rol de administrador")

@router.post("/roles", response_model=RolResponse, status_code=status.HTTP_201_CREATED)
def crear_rol(
    datos: RolCreate,
    current_user: Usuario = Depends(require_permission("ROLES_MANAGE")),
    db: Session = Depends(get_db)
):
    codigo = _codigo_desde_nombre(datos.codigo or datos.nombre)
    if not codigo:
        raise HTTPException(status_code=400, detail="El nombre del rol debe contener letras o números")
    if db.query(Rol).filter(Rol.codigo == codigo).first():
        raise HTTPException(status_code=400, detail=f"Ya existe un rol con el código {codigo}")
    _permisos_validos(datos.permiso_ids, current_user, db)

    rol = Rol(codigo=codigo, nombre=datos.nombre, descripcion=datos.descripcion, es_sistema=False)
    db.add(rol)
    db.flush()
    db.add_all([RolPermiso(rol_id=rol.id, permiso_id=pid) for pid in set(datos.permiso_ids)])
    db.commit()
    db.refresh(rol)
    return rol

@router.get("/permisos", response_model=List[PermisoResponse])
def listar_permisos(
    current_user: Usuario = Depends(require_permission("USUARIOS_MANAGE", "ROLES_MANAGE")),
    db: Session = Depends(get_db)
):
    return db.query(Permiso).all()

@router.post("/roles/{rol_id}/permisos", response_model=List[PermisoResponse])
def asignar_permisos_a_rol(
    rol_id: UUID,
    permiso_ids: List[UUID],
    current_user: Usuario = Depends(require_permission("ROLES_MANAGE")),
    db: Session = Depends(get_db)
):
    """
    Asigna o reemplaza el listado de permisos asociados a un rol específico.
    """
    rol = db.query(Rol).filter(Rol.id == rol_id).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    _validar_edicion_de_rol(str(rol.codigo), rol.id, current_user)
    _permisos_validos(permiso_ids, current_user, db)

    # Eliminar asignaciones previas
    db.query(RolPermiso).filter(RolPermiso.rol_id == rol_id).delete()

    # Agregar nuevas asignaciones
    nuevas_relaciones = [RolPermiso(rol_id=rol_id, permiso_id=pid) for pid in set(permiso_ids)]
    db.add_all(nuevas_relaciones)
    db.commit()

    # Retornar permisos actuales del rol
    permisos = (
        db.query(Permiso)
        .join(RolPermiso, RolPermiso.permiso_id == Permiso.id)
        .filter(RolPermiso.rol_id == rol_id)
        .all()
    )
    return permisos

@router.get("/roles/{rol_id}/permisos", response_model=List[PermisoResponse])
def obtener_permisos_de_rol(
    rol_id: UUID,
    current_user: Usuario = Depends(require_permission("ROLES_MANAGE")),
    db: Session = Depends(get_db)
):
    rol = db.query(Rol).filter(Rol.id == rol_id).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return (
        db.query(Permiso)
        .join(RolPermiso, RolPermiso.permiso_id == Permiso.id)
        .filter(RolPermiso.rol_id == rol_id)
        .all()
    )

# ==================== USUARIOS ====================

def _validar_no_deja_sin_administrador(usuario: Usuario, cambios: dict, current_user: Usuario, db: Session) -> None:
    """Sin administrador activo nadie podría entrar a corregirlo desde el sistema."""
    if not es_admin(usuario):
        return
    se_desactiva = cambios.get("activo") is False
    rol_nuevo = cambios.get("rol_id")
    pierde_rol = bool(rol_nuevo) and rol_nuevo != usuario.rol_id
    if not se_desactiva and not pierde_rol:
        return
    if usuario.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes desactivar tu propia cuenta ni quitarte el rol de administrador")
    otros = db.query(Usuario.id).filter(Usuario.rol_id == usuario.rol_id, Usuario.activo.is_(True), Usuario.id != usuario.id).first()
    if not otros:
        raise HTTPException(status_code=400, detail="Debe quedar al menos un administrador activo")

@router.get("/", response_model=List[UsuarioDetailResponse])
def listar_usuarios(
    current_user: Usuario = Depends(require_permission("USUARIOS_MANAGE")),
    db: Session = Depends(get_db)
):
    return db.query(Usuario).all()

@router.post("/", response_model=UsuarioDetailResponse, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    datos: UsuarioCreate,
    current_user: Usuario = Depends(require_permission("USUARIOS_MANAGE")),
    db: Session = Depends(get_db)
):
    if db.query(Usuario).filter(Usuario.username == datos.username).first():
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está en uso")
    if db.query(Usuario).filter(Usuario.email == datos.email).first():
        raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado")
    _validar_rol_asignable(datos.rol_id, current_user, db)

    user_dict = datos.model_dump(exclude={"password", "doctor_perfil", "asistente_perfil"})
    user_dict["password_hash"] = hash_password(datos.password)
    # La contraseña inicial la conoce quien crea la cuenta: se cambia al primer ingreso
    user_dict["debe_cambiar_contrasena"] = True

    nuevo_usuario = Usuario(**user_dict)
    db.add(nuevo_usuario)
    db.flush()

    # Si se especificó perfil de doctor o el rol es DOCTOR
    rol = db.query(Rol).filter(Rol.id == datos.rol_id).first()
    if datos.doctor_perfil or (rol and rol.codigo == "DOCTOR"):
        doc_data = datos.doctor_perfil.model_dump() if datos.doctor_perfil else {}
        db.add(Doctor(usuario_id=nuevo_usuario.id, **doc_data))

    # Si se especificó perfil de asistente o el rol es ASISTENTE
    if datos.asistente_perfil or (rol and rol.codigo == "ASISTENTE"):
        asist_data = datos.asistente_perfil.model_dump() if datos.asistente_perfil else {}
        db.add(Asistente(usuario_id=nuevo_usuario.id, **asist_data))

    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

@router.get("/{id}", response_model=UsuarioDetailResponse)
def obtener_usuario(
    id: UUID,
    current_user: Usuario = Depends(require_permission("USUARIOS_MANAGE")),
    db: Session = Depends(get_db)
):
    usuario = db.query(Usuario).filter(Usuario.id == id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario

@router.put("/{id}", response_model=UsuarioDetailResponse)
def actualizar_usuario(
    id: UUID,
    datos: UsuarioUpdate,
    current_user: Usuario = Depends(require_permission("USUARIOS_MANAGE")),
    db: Session = Depends(get_db)
):
    usuario = db.query(Usuario).filter(Usuario.id == id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not es_admin(current_user) and (es_admin(usuario) or usuario.id == current_user.id):
        raise HTTPException(status_code=403, detail="No puedes modificar a un administrador ni tu propia cuenta")

    update_dict = datos.model_dump(exclude_unset=True)
    if update_dict.get("rol_id"):
        _validar_rol_asignable(update_dict["rol_id"], current_user, db)
    _validar_no_deja_sin_administrador(usuario, update_dict, current_user, db)
    doc_update = update_dict.pop("doctor_perfil", None)
    asist_update = update_dict.pop("asistente_perfil", None)

    if "password" in update_dict and update_dict["password"]:
        update_dict["password_hash"] = hash_password(update_dict.pop("password"))
        # Quien la restablece la conoce: se cierran las sesiones y debe cambiarla al entrar
        update_dict["version_sesion"] = usuario.version_sesion + 1
        update_dict["debe_cambiar_contrasena"] = usuario.id != current_user.id
    elif "password" in update_dict:
        update_dict.pop("password")

    for field, value in update_dict.items():
        setattr(usuario, field, value)

    if doc_update and usuario.doctor_perfil:
        for f, v in doc_update.items():
            setattr(usuario.doctor_perfil, f, v)

    if asist_update and usuario.asistente_perfil:
        for f, v in asist_update.items():
            setattr(usuario.asistente_perfil, f, v)

    db.commit()
    db.refresh(usuario)
    return usuario

# ==================== DOCTORES ====================

@router.get("/doctores/lista", response_model=List[DoctorResponse])
def listar_doctores(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(Doctor).all()

@router.post("/doctores/perfil", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
def crear_perfil_doctor(
    datos: DoctorCreate,
    current_user: Usuario = Depends(require_permission("USUARIOS_MANAGE")),
    db: Session = Depends(get_db)
):
    if db.query(Doctor).filter(Doctor.usuario_id == datos.usuario_id).first():
        raise HTTPException(status_code=400, detail="Este usuario ya tiene perfil de doctor")
    doctor = Doctor(**datos.model_dump())
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor

@router.put("/doctores/{id}", response_model=DoctorResponse)
def actualizar_doctor(
    id: UUID,
    datos: DoctorUpdate,
    current_user: Usuario = Depends(require_permission("USUARIOS_MANAGE")),
    db: Session = Depends(get_db)
):
    doctor = db.query(Doctor).filter(Doctor.id == id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Perfil de doctor no encontrado")
    for field, value in datos.model_dump(exclude_unset=True).items():
        setattr(doctor, field, value)
    db.commit()
    db.refresh(doctor)
    return doctor

# ==================== ASISTENTES ====================

@router.get("/asistentes/lista", response_model=List[AsistenteResponse])
def listar_asistentes(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(Asistente).all()

@router.post("/asistentes/perfil", response_model=AsistenteResponse, status_code=status.HTTP_201_CREATED)
def crear_perfil_asistente(
    datos: AsistenteCreate,
    current_user: Usuario = Depends(require_permission("USUARIOS_MANAGE")),
    db: Session = Depends(get_db)
):
    if db.query(Asistente).filter(Asistente.usuario_id == datos.usuario_id).first():
        raise HTTPException(status_code=400, detail="Este usuario ya tiene perfil de asistente")
    asistente = Asistente(**datos.model_dump())
    db.add(asistente)
    db.commit()
    db.refresh(asistente)
    return asistente
