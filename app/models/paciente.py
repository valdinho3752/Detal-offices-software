import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Date, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.models.enums import GeneroEnum, EstadoRegistroEnum

class Paciente(Base):
    __tablename__ = "pacientes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombres = Column(String(120), nullable=False)
    apellidos = Column(String(120), nullable=False)
    tipo_documento = Column(String(20), default="DNI", nullable=False)
    numero_documento = Column(String(50), unique=True, nullable=False)
    fecha_nacimiento = Column(Date, nullable=False)
    genero = Column(ENUM(GeneroEnum, name="genero_enum", create_type=False), default=GeneroEnum.OTRO)
    telefono = Column(String(30), nullable=False)
    email = Column(String(150), nullable=True)
    direccion = Column(Text, nullable=True)
    ocupacion = Column(String(100), nullable=True)
    contacto_emergencia_nombre = Column(String(150), nullable=True)
    contacto_emergencia_telefono = Column(String(30), nullable=True)
    estado = Column(ENUM(EstadoRegistroEnum, name="estado_registro_enum", create_type=False), default=EstadoRegistroEnum.ACTIVO, nullable=False)
    reactivado_en = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relaciones
    antecedentes = relationship("AntecedenteMedico", back_populates="paciente", uselist=False, cascade="all, delete-orphan")
    odontogramas = relationship("Odontograma", back_populates="paciente", cascade="all, delete-orphan")
    planes = relationship("PlanTratamiento", back_populates="paciente", cascade="all, delete-orphan")
    citas = relationship("Cita", back_populates="paciente", cascade="all, delete-orphan")
    visitas = relationship("VisitaEvolucion", back_populates="paciente", cascade="all, delete-orphan")
    radiografias = relationship("RadiografiaEstudio", back_populates="paciente", cascade="all, delete-orphan")
    pagos = relationship("Pago", back_populates="paciente", cascade="all, delete-orphan")
    ordenes_protesis = relationship("OrdenLaboratorioProtesis", back_populates="paciente", cascade="all, delete-orphan")

class AntecedenteMedico(Base):
    __tablename__ = "antecedentes_medicos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paciente_id = Column(UUID(as_uuid=True), ForeignKey("pacientes.id", ondelete="CASCADE"), unique=True, nullable=False)
    enfermedades_sistemicas = Column(Text, nullable=True)
    alergias = Column(Text, nullable=True)
    medicamentos_actuales = Column(Text, nullable=True)
    cirugias_previas = Column(Text, nullable=True)
    fuma = Column(Boolean, default=False)
    embarazada = Column(Boolean, default=False)
    observaciones = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    paciente = relationship("Paciente", back_populates="antecedentes")
