import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from app.database import Base
from app.models.enums import CategoriaTratamientoEnum, EstadoPlanEnum, EstadoItemPlanEnum

class CatalogoTratamiento(Base):
    __tablename__ = "catalogo_tratamientos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo = Column(String(30), unique=True, nullable=False)
    categoria = Column(ENUM(CategoriaTratamientoEnum, name="categoria_tratamiento_enum", create_type=False), nullable=False)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=True)
    costo_base = Column(Numeric(12, 2), default=0.00, nullable=False)
    duracion_estimada_min = Column(Integer, default=30, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    items_plan = relationship("ItemPlanTratamiento", back_populates="tratamiento")

class PlanTratamiento(Base):
    __tablename__ = "planes_tratamiento"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paciente_id = Column(UUID(as_uuid=True), ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctores.id"), nullable=False)
    titulo = Column(String(200), nullable=False)
    estado = Column(ENUM(EstadoPlanEnum, name="estado_plan_enum", create_type=False), default=EstadoPlanEnum.PROPUESTO, nullable=False)
    costo_total = Column(Numeric(12, 2), default=0.00, nullable=False)
    fecha_creacion = Column(Date, default=func.current_date(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    paciente = relationship("Paciente", back_populates="planes")
    doctor = relationship("Doctor", back_populates="planes")
    items = relationship("ItemPlanTratamiento", back_populates="plan", cascade="all, delete-orphan", order_by="ItemPlanTratamiento.orden_secuencia")
    pagos = relationship("Pago", back_populates="plan")

class ItemPlanTratamiento(Base):
    __tablename__ = "items_plan_tratamiento"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("planes_tratamiento.id", ondelete="CASCADE"), nullable=False)
    tratamiento_id = Column(UUID(as_uuid=True), ForeignKey("catalogo_tratamientos.id"), nullable=False)
    hallazgo_superficie_id = Column(UUID(as_uuid=True), ForeignKey("hallazgos_superficie.id", ondelete="SET NULL"), nullable=True)
    pieza_fdi = Column(Integer, nullable=True)
    orden_secuencia = Column(Integer, default=1, nullable=False)
    fecha_programada = Column(Date, nullable=True)
    estado = Column(ENUM(EstadoItemPlanEnum, name="estado_item_plan_enum", create_type=False), default=EstadoItemPlanEnum.PENDIENTE, nullable=False)
    costo_acordado = Column(Numeric(12, 2), nullable=False)
    observaciones = Column(Text, nullable=True)
    fecha_realizacion = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    plan = relationship("PlanTratamiento", back_populates="items")
    tratamiento = relationship("CatalogoTratamiento", back_populates="items_plan")
    hallazgo = relationship("HallazgoSuperficie", back_populates="item_plan")
    citas = relationship("Cita", back_populates="item_plan")
    visitas_realizadas = relationship("VisitaEvolucion", foreign_keys="VisitaEvolucion.item_plan_id", back_populates="item_plan")
    visitas_programadas = relationship("VisitaEvolucion", foreign_keys="VisitaEvolucion.proximo_item_plan_id", back_populates="proximo_item_plan")
    ordenes_protesis = relationship("OrdenLaboratorioProtesis", back_populates="item_plan")

    @validates("estado")
    def _fechar_realizacion(self, _clave, estado):
        """Aplica a cualquier cambio de estado; quien conozca la fecha real, como la cita, la ajusta después."""
        if estado != EstadoItemPlanEnum.COMPLETADO:
            self.fecha_realizacion = None
        elif self.estado != EstadoItemPlanEnum.COMPLETADO:
            self.fecha_realizacion = datetime.now(timezone.utc)
        return estado

    @property
    def es_proxima_sesion(self) -> bool:
        return self.estado == EstadoItemPlanEnum.PROXIMA_SESION

    @es_proxima_sesion.setter
    def es_proxima_sesion(self, value):
        if value:
            self.estado = EstadoItemPlanEnum.PROXIMA_SESION

    @property
    def precio_unitario(self):
        return self.costo_acordado

    @precio_unitario.setter
    def precio_unitario(self, value):
        if value is not None and self.costo_acordado is None:
            self.costo_acordado = value

    @property
    def descuento(self):
        return Decimal("0.00")

    @descuento.setter
    def descuento(self, value):
        pass

    @property
    def superficie(self):
        if self.hallazgo and self.hallazgo.superficie:
            val = self.hallazgo.superficie
            return val.value if hasattr(val, "value") else str(val)
        if self.observaciones and "Superficie: " in self.observaciones:
            part = self.observaciones.split("Superficie: ")[1]
            return part.split(" |")[0].split("\n")[0].strip()
        return None

    @superficie.setter
    def superficie(self, value):
        pass
