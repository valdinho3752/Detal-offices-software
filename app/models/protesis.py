import uuid
from sqlalchemy import Column, String, DateTime, Date, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.models.enums import TipoTrabajoProtesisEnum, EstadoOrdenProtesisEnum

class OrdenLaboratorioProtesis(Base):
    __tablename__ = "ordenes_laboratorio_protesis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paciente_id = Column(UUID(as_uuid=True), ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctores.id"), nullable=False)
    item_plan_id = Column(UUID(as_uuid=True), ForeignKey("items_plan_tratamiento.id", ondelete="SET NULL"), nullable=True)
    egreso_caja_id = Column(UUID(as_uuid=True), ForeignKey("egresos_caja.id", ondelete="SET NULL"), nullable=True)
    laboratorio_nombre = Column(String(150), nullable=False)
    tipo_trabajo = Column(ENUM(TipoTrabajoProtesisEnum, name="tipo_trabajo_protesis_enum", create_type=False), nullable=False)
    piezas_dentales = Column(String(100), nullable=False)
    color_guia_vita = Column(String(50), nullable=True)
    instrucciones_tecnicas = Column(Text, nullable=True)
    costo_laboratorio = Column(Numeric(12, 2), default=0.00, nullable=False)
    fecha_envio = Column(Date, default=func.current_date(), nullable=False)
    fecha_entrega_esperada = Column(Date, nullable=False)
    fecha_recepcion_real = Column(Date, nullable=True)
    estado = Column(ENUM(EstadoOrdenProtesisEnum, name="estado_orden_protesis_enum", create_type=False), default=EstadoOrdenProtesisEnum.ENVIADO, nullable=False)
    observaciones = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    paciente = relationship("Paciente", back_populates="ordenes_protesis")
    doctor = relationship("Doctor", back_populates="ordenes_protesis")
    item_plan = relationship("ItemPlanTratamiento", back_populates="ordenes_protesis")
    egreso_caja = relationship("EgresoCaja", back_populates="orden_protesis")
