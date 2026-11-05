import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.models.enums import RolCodigoEnum

class Rol(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo = Column(String(50), unique=True, nullable=False)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    es_sistema = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    usuarios = relationship("Usuario", back_populates="rol")
    permisos_asociados = relationship("RolPermiso", back_populates="rol", cascade="all, delete-orphan")

class Permiso(Base):
    __tablename__ = "permisos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    modulo = Column(String(100), nullable=False)
    accion = Column(String(50), nullable=False)
    codigo_permiso = Column(String(150), unique=True, nullable=False)
    descripcion = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    roles_asociados = relationship("RolPermiso", back_populates="permiso", cascade="all, delete-orphan")

class RolPermiso(Base):
    __tablename__ = "roles_permisos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rol_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permiso_id = Column(UUID(as_uuid=True), ForeignKey("permisos.id", ondelete="CASCADE"), nullable=False)

    rol = relationship("Rol", back_populates="permisos_asociados")
    permiso = relationship("Permiso", back_populates="roles_asociados")

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rol_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    telefono = Column(String(30), nullable=True)
    activo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relaciones
    rol = relationship("Rol", back_populates="usuarios")
    permisos_especiales = relationship("UsuarioPermisoEspecial", back_populates="usuario", cascade="all, delete-orphan")
    doctor_perfil = relationship("Doctor", back_populates="usuario", uselist=False, cascade="all, delete-orphan")
    asistente_perfil = relationship("Asistente", back_populates="usuario", uselist=False, cascade="all, delete-orphan")
    contrato = relationship("ContratoRemuneracion", back_populates="usuario", uselist=False, cascade="all, delete-orphan")
    asistencias = relationship("RegistroAsistencia", back_populates="usuario", cascade="all, delete-orphan")
    auditorias = relationship("AuditoriaLog", back_populates="usuario")

class UsuarioPermisoEspecial(Base):
    __tablename__ = "usuarios_permisos_especiales"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    permiso_id = Column(UUID(as_uuid=True), ForeignKey("permisos.id", ondelete="CASCADE"), nullable=False)
    concedido = Column(Boolean, default=True, nullable=False)

    usuario = relationship("Usuario", back_populates="permisos_especiales")
    permiso = relationship("Permiso")

class Doctor(Base):
    __tablename__ = "doctores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True, nullable=False)
    especialidad = Column(String(120), default="Odontología General", nullable=False)
    numero_colegiatura = Column(String(60), nullable=True)
    color_agenda = Column(String(10), default="#3B82F6")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    usuario = relationship("Usuario", back_populates="doctor_perfil")
    citas = relationship("Cita", back_populates="doctor")
    odontogramas = relationship("Odontograma", back_populates="doctor")
    planes = relationship("PlanTratamiento", back_populates="doctor")
    visitas = relationship("VisitaEvolucion", back_populates="doctor")
    ordenes_protesis = relationship("OrdenLaboratorioProtesis", back_populates="doctor")

class Asistente(Base):
    __tablename__ = "asistentes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True, nullable=False)
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    usuario = relationship("Usuario", back_populates="asistente_perfil")
    visitas_asistidas = relationship("VisitaEvolucion", back_populates="asistente")
