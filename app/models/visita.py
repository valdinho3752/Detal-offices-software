import uuid
from sqlalchemy import Boolean, Column, String, DateTime, Date, ForeignKey, Text
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
    generada_automaticamente = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    paciente = relationship("Paciente", back_populates="visitas")
    doctor = relationship("Doctor", back_populates="visitas")
    asistente = relationship("Asistente", back_populates="visitas_asistidas")
    cita = relationship("Cita", back_populates="visita")
    item_plan = relationship("ItemPlanTratamiento", foreign_keys=[item_plan_id], back_populates="visitas_realizadas")
    proximo_item_plan = relationship("ItemPlanTratamiento", foreign_keys=[proximo_item_plan_id], back_populates="visitas_programadas")
    radiografias = relationship("RadiografiaEstudio", back_populates="visita")
    pagos = relationship("Pago", back_populates="visita")
    observaciones = relationship(
        "ObservacionEvolucion",
        back_populates="visita",
        cascade="all, delete-orphan",
        order_by="ObservacionEvolucion.created_at",
    )

    @property
    def doctor_nombre(self):
        return self.doctor.nombre_completo if self.doctor else None


class ObservacionEvolucion(Base):
    """Observación de un doctor o asistente: solo se agrega, nunca se edita ni elimina."""
    __tablename__ = "observaciones_evolucion"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visita_id = Column(UUID(as_uuid=True), ForeignKey("visitas_evolucion.id", ondelete="CASCADE"), nullable=False)
    autor_usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    rol_autor = Column(String(50), nullable=False)
    texto = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    visita = relationship("VisitaEvolucion", back_populates="observaciones")
    autor = relationship("Usuario")

    @property
    def autor_nombre(self):
        return f"{self.autor.nombre} {self.autor.apellido}" if self.autor else None
