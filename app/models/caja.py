import uuid
from sqlalchemy import Boolean, Column, String, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.models.enums import EstadoCajaEnum, MetodoPagoEnum, CategoriaEgresoCajaEnum, TipoPagoEmpleadoEnum

class CajaSesion(Base):
    __tablename__ = "cajas_sesiones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_apertura_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    usuario_cierre_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    fecha_apertura = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    fecha_cierre = Column(DateTime(timezone=True), nullable=True)
    monto_inicial_fondo = Column(Numeric(12, 2), default=0.00, nullable=False)
    total_ingresos_efectivo = Column(Numeric(12, 2), default=0.00, nullable=False)
    total_egresos_efectivo = Column(Numeric(12, 2), default=0.00, nullable=False)
    saldo_efectivo_esperado = Column(Numeric(12, 2), default=0.00, nullable=False)
    total_efectivo_contado = Column(Numeric(12, 2), nullable=True)
    diferencia_descuadre = Column(Numeric(12, 2), nullable=True)
    estado = Column(ENUM(EstadoCajaEnum, name="estado_caja_enum", create_type=False), default=EstadoCajaEnum.ABIERTA, nullable=False)
    observaciones = Column(Text, nullable=True)

    usuario_apertura = relationship("Usuario", foreign_keys=[usuario_apertura_id])
    usuario_cierre = relationship("Usuario", foreign_keys=[usuario_cierre_id])
    pagos = relationship("Pago", back_populates="caja_sesion")
    egresos = relationship("EgresoCaja", back_populates="caja_sesion")
    pagos_empleados = relationship("PagoEmpleado", back_populates="caja_sesion")

class Pago(Base):
    __tablename__ = "pagos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paciente_id = Column(UUID(as_uuid=True), ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("planes_tratamiento.id", ondelete="SET NULL"), nullable=True)
    visita_id = Column(UUID(as_uuid=True), ForeignKey("visitas_evolucion.id", ondelete="SET NULL"), nullable=True)
    caja_sesion_id = Column(UUID(as_uuid=True), ForeignKey("cajas_sesiones.id", ondelete="SET NULL"), nullable=True)
    doctor_comision_id = Column(UUID(as_uuid=True), ForeignKey("doctores.id", ondelete="SET NULL"), nullable=True)
    registrado_por_usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    monto = Column(Numeric(12, 2), nullable=False)
    metodo_pago = Column(ENUM(MetodoPagoEnum, name="metodo_pago_enum", create_type=False), default=MetodoPagoEnum.EFECTIVO, nullable=False)
    referencia_comprobante = Column(String(150), nullable=True)
    es_cobro_directo = Column(Boolean, default=False, nullable=False)
    cobro_cita_id = Column(UUID(as_uuid=True), ForeignKey("cobros_cita.id", ondelete="SET NULL"), nullable=True)
    fecha_hora = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    observaciones = Column(Text, nullable=True)

    paciente = relationship("Paciente", back_populates="pagos")
    plan = relationship("PlanTratamiento", back_populates="pagos")
    visita = relationship("VisitaEvolucion", back_populates="pagos")
    caja_sesion = relationship("CajaSesion", back_populates="pagos")
    doctor_comision = relationship("Doctor")
    registrado_por = relationship("Usuario", foreign_keys=[registrado_por_usuario_id])
    cobro_cita = relationship("CobroCita", back_populates="pagos")

class PagoEmpleado(Base):
    __tablename__ = "pagos_empleados"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_empleado_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    caja_sesion_id = Column(UUID(as_uuid=True), ForeignKey("cajas_sesiones.id", ondelete="SET NULL"), nullable=True)
    usuario_autoriza_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    tipo_pago = Column(ENUM(TipoPagoEmpleadoEnum, name="tipo_pago_empleado_enum", create_type=False), nullable=False)
    monto_base = Column(Numeric(12, 2), default=0.00)
    monto_comisiones = Column(Numeric(12, 2), default=0.00)
    deducciones_descuentos = Column(Numeric(12, 2), default=0.00)
    monto_neto_pagado = Column(Numeric(12, 2), nullable=False)
    metodo_pago = Column(String(50), default="EFECTIVO_CAJA", nullable=False)
    referencia_pago = Column(String(150), nullable=True)
    fecha_hora_pago = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    observaciones = Column(Text, nullable=True)

    usuario_empleado = relationship("Usuario", foreign_keys=[usuario_empleado_id])
    caja_sesion = relationship("CajaSesion", back_populates="pagos_empleados")
    usuario_autoriza = relationship("Usuario", foreign_keys=[usuario_autoriza_id])
    egreso = relationship("EgresoCaja", back_populates="pago_empleado", uselist=False)

class EgresoCaja(Base):
    __tablename__ = "egresos_caja"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    caja_sesion_id = Column(UUID(as_uuid=True), ForeignKey("cajas_sesiones.id", ondelete="CASCADE"), nullable=False)
    usuario_autoriza_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    usuario_beneficiario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    pago_empleado_id = Column(UUID(as_uuid=True), ForeignKey("pagos_empleados.id", ondelete="SET NULL"), nullable=True)
    categoria = Column(ENUM(CategoriaEgresoCajaEnum, name="categoria_egreso_caja_enum", create_type=False), nullable=False)
    monto = Column(Numeric(12, 2), nullable=False)
    concepto_motivo = Column(String(255), nullable=False)
    numero_recibo_comprobante = Column(String(100), nullable=True)
    fecha_hora = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    caja_sesion = relationship("CajaSesion", back_populates="egresos")
    usuario_autoriza = relationship("Usuario", foreign_keys=[usuario_autoriza_id])
    usuario_beneficiario = relationship("Usuario", foreign_keys=[usuario_beneficiario_id])
    pago_empleado = relationship("PagoEmpleado", back_populates="egreso")
    orden_protesis = relationship("OrdenLaboratorioProtesis", back_populates="egreso_caja", uselist=False)
