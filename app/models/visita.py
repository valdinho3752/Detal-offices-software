import uuid
from sqlalchemy import Column, String, DateTime, Date, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class VisitaEvolucion(Base):
    __tablename__ = "visitas_evolucion"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paciente_id = Column(UUID(as_uuid=True), ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctores.id"), nullable=False)
    asistente_id = Column(UUID(as_uuid=True), ForeignKey("asistentes.id", ondelete="SET NULL"), nullable=True)
    cita_id = Column(UUID(as_uuid=True), ForeignKey("citas.id", ondelete="SET NULL"), unique=True, nullable=True)
    item_plan_id = Column(UUID(as_uuid=True), ForeignKey("items_plan_tratamiento.id", ondelete="SET NULL"), nullable=True)
    proximo_item_plan_id = Column(UUID(as_uuid=True), ForeignKey("items_plan_tratamiento.id", ondelete="SET NULL"), nullable=True)
    fecha_hora = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    motivo_visita = Column(Text, nullable=False)
    diagnostico = Column(Text, nullable=False)
    procedimiento_realizado = Column(Text, nullable=False)
    receta_medicamentos = Column(Text, nullable=True)
    recomendaciones = Column(Text, nullable=True)
    fecha_proximo_control = Column(Date, nullable=True)
    indicaciones_proxima_visita = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    paciente = relationship("Paciente", back_populates="visitas")
    doctor = relationship("Doctor", back_populates="visitas")
    asistente = relationship("Asistente", back_populates="visitas_asistidas")
    cita = relationship("Cita", back_populates="visita")
    item_plan = relationship("ItemPlanTratamiento", foreign_keys=[item_plan_id], back_populates="visitas_realizadas")
    proximo_item_plan = relationship("ItemPlanTratamiento", foreign_keys=[proximo_item_plan_id], back_populates="visitas_programadas")
    radiografias = relationship("RadiografiaEstudio", back_populates="visita")
    pagos = relationship("Pago", back_populates="visita")
