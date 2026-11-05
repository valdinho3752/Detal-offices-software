import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Date, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.models.enums import AsistenciaTipoEnum, TipoRemuneracionEnum

class ContratoRemuneracion(Base):
    __tablename__ = "contratos_remuneracion"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True, nullable=False)
    tipo_remuneracion = Column(ENUM(TipoRemuneracionEnum, name="tipo_remuneracion_enum", create_type=False), default=TipoRemuneracionEnum.SUELDO_FIJO_MENSUAL, nullable=False)
    salario_base = Column(Numeric(12, 2), default=0.00, nullable=False)
    porcentaje_comision = Column(Numeric(5, 2), default=0.00, nullable=False)
    valor_hora = Column(Numeric(10, 2), default=0.00, nullable=False)
    fecha_inicio_contrato = Column(Date, default=func.current_date(), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    usuario = relationship("Usuario", back_populates="contrato")

class RegistroAsistencia(Base):
    __tablename__ = "registro_asistencia"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    tipo_evento = Column(ENUM(AsistenciaTipoEnum, name="asistencia_tipo_enum", create_type=False), nullable=False)
    fecha_hora = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    observaciones = Column(Text, nullable=True)
    ip_registro = Column(String(45), nullable=True)

    usuario = relationship("Usuario", back_populates="asistencias")
