import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.models.enums import EstadoCitaEnum

class Cita(Base):
    __tablename__ = "citas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paciente_id = Column(UUID(as_uuid=True), ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctores.id"), nullable=False)
    item_plan_id = Column(UUID(as_uuid=True), ForeignKey("items_plan_tratamiento.id", ondelete="SET NULL"), nullable=True)
    tratamiento_id = Column(UUID(as_uuid=True), ForeignKey("catalogo_tratamientos.id", ondelete="SET NULL"), nullable=True)
    fecha_inicio_programada = Column(DateTime(timezone=True), nullable=False)
    fecha_fin_programada = Column(DateTime(timezone=True), nullable=False)
    hora_llegada_recepcion = Column(DateTime(timezone=True), nullable=True)
    hora_inicio_sillon = Column(DateTime(timezone=True), nullable=True)
    hora_fin_sillon = Column(DateTime(timezone=True), nullable=True)
    duracion_sillon_minutos = Column(Integer, nullable=True)
    estado = Column(ENUM(EstadoCitaEnum, name="estado_cita_enum", create_type=False), default=EstadoCitaEnum.PROGRAMADA, nullable=False)
    motivo_consulta = Column(String(255), nullable=False)
    notas_adicionales = Column(Text, nullable=True)
    created_by_usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    paciente = relationship("Paciente", back_populates="citas")
    doctor = relationship("Doctor", back_populates="citas")
    item_plan = relationship("ItemPlanTratamiento", back_populates="citas")
    tratamiento = relationship("CatalogoTratamiento", backref="citas")
    visita = relationship("VisitaEvolucion", back_populates="cita", uselist=False)
