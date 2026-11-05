import uuid
from decimal import Decimal
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.models.enums import EstadoCobroCitaEnum, EstadoPlanEnum

# Solo un plan aceptado genera deuda: lo cobrado en él descuenta su saldo
ESTADOS_PLAN_CON_DEUDA = (EstadoPlanEnum.APROBADO, EstadoPlanEnum.EN_CURSO, EstadoPlanEnum.COMPLETADO)


class CobroCita(Base):
    """Cuenta que se crea al finalizar una cita y se puede editar hasta confirmar el pago."""
    __tablename__ = "cobros_cita"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cita_id = Column(UUID(as_uuid=True), ForeignKey("citas.id", ondelete="SET NULL"), unique=True, nullable=True)
    paciente_id = Column(UUID(as_uuid=True), ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctores.id"), nullable=False)
    estado = Column(ENUM(EstadoCobroCitaEnum, name="estado_cobro_cita_enum", create_type=False), default=EstadoCobroCitaEnum.PENDIENTE, nullable=False)
    motivo_cierre = Column(Text, nullable=True)
    cerrado_por_usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    fecha_cierre = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    cita = relationship("Cita", back_populates="cobro")
    paciente = relationship("Paciente")
    doctor = relationship("Doctor")
    lineas = relationship("CobroCitaLinea", back_populates="cobro", cascade="all, delete-orphan", order_by="CobroCitaLinea.item_plan_id.is_(None), CobroCitaLinea.concepto")
    pagos = relationship("Pago", back_populates="cobro_cita")

    @property
    def total(self) -> Decimal:
        return sum((linea.monto or Decimal("0") for linea in self.lineas), Decimal("0"))

    @property
    def paciente_nombre(self):
        return f"{self.paciente.nombres} {self.paciente.apellidos}" if self.paciente else None

    @property
    def doctor_nombre(self):
        return self.doctor.nombre_completo if self.doctor else None

    @property
    def fecha_cita(self):
        return self.cita.fecha_inicio_programada if self.cita else None

    @property
    def motivo_cita(self):
        return self.cita.motivo_consulta if self.cita else None


class CobroCitaLinea(Base):
    __tablename__ = "cobros_cita_lineas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cobro_id = Column(UUID(as_uuid=True), ForeignKey("cobros_cita.id", ondelete="CASCADE"), nullable=False)
    item_plan_id = Column(UUID(as_uuid=True), ForeignKey("items_plan_tratamiento.id", ondelete="SET NULL"), nullable=True)
    concepto = Column(String(255), nullable=False)
    monto = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    costo_referencia = Column(Numeric(12, 2), nullable=True)

    cobro = relationship("CobroCita", back_populates="lineas")
    item_plan = relationship("ItemPlanTratamiento")

    @property
    def plan_con_deuda(self):
        """Plan aprobado al que se aplica esta línea; sin él, la línea es un cobro directo."""
        plan = self.item_plan.plan if self.item_plan else None
        return plan if plan and plan.estado in ESTADOS_PLAN_CON_DEUDA else None

    @property
    def aplica_a_plan(self) -> bool:
        return self.plan_con_deuda is not None

    @property
    def plan_titulo(self):
        plan = self.plan_con_deuda
        return plan.titulo if plan else None
