import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.models.enums import (
    TipoDenticionEnum,
    TipoOdontogramaEnum,
    EstadoDienteEnum,
    SuperficieDentalEnum,
    CondicionDentalEnum,
    EstadoClinicoHallazgoEnum,
)

class Odontograma(Base):
    __tablename__ = "odontogramas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paciente_id = Column(UUID(as_uuid=True), ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctores.id"), nullable=False)
    tipo_denticion = Column(ENUM(TipoDenticionEnum, name="tipo_denticion_enum", create_type=False), default=TipoDenticionEnum.ADULTA_PERMANENTE, nullable=False)
    tipo_registro = Column(ENUM(TipoOdontogramaEnum, name="tipo_odontograma_enum", create_type=False), default=TipoOdontogramaEnum.INICIAL_INGRESO, nullable=False)
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    observaciones_generales = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    paciente = relationship("Paciente", back_populates="odontogramas")
    doctor = relationship("Doctor", back_populates="odontogramas")
    piezas = relationship("PiezaDental", back_populates="odontograma", cascade="all, delete-orphan", order_by="PiezaDental.numero_fdi")

class PiezaDental(Base):
    __tablename__ = "piezas_dentales"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    odontograma_id = Column(UUID(as_uuid=True), ForeignKey("odontogramas.id", ondelete="CASCADE"), nullable=False)
    numero_fdi = Column(Integer, nullable=False) # 11-48, 51-85
    estado_general = Column(ENUM(EstadoDienteEnum, name="estado_diente_enum", create_type=False), default=EstadoDienteEnum.PRESENTE, nullable=False)
    tiene_endodoncia = Column(Boolean, default=False, nullable=False)
    tiene_perno_poste = Column(Boolean, default=False, nullable=False)
    notas_pieza = Column(Text, nullable=True)

    odontograma = relationship("Odontograma", back_populates="piezas")
    hallazgos = relationship("HallazgoSuperficie", back_populates="pieza", cascade="all, delete-orphan")

class HallazgoSuperficie(Base):
    __tablename__ = "hallazgos_superficie"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pieza_dental_id = Column(UUID(as_uuid=True), ForeignKey("piezas_dentales.id", ondelete="CASCADE"), nullable=False)
    superficie = Column(ENUM(SuperficieDentalEnum, name="superficie_dental_enum", create_type=False), nullable=False)
    condicion = Column(ENUM(CondicionDentalEnum, name="condicion_dental_enum", create_type=False), nullable=False)
    estado_clinico = Column(ENUM(EstadoClinicoHallazgoEnum, name="estado_clinico_hallazgo_enum", create_type=False), nullable=False)
    color_hex = Column(String(10), default="#FF0000")
    detalle = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    pieza = relationship("PiezaDental", back_populates="hallazgos")
    item_plan = relationship("ItemPlanTratamiento", back_populates="hallazgo", uselist=False)
