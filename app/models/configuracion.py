from sqlalchemy import CheckConstraint, Column, DateTime, Integer, LargeBinary, String
from sqlalchemy.sql import func
from app.database import Base

class EstadoCopias(Base):
    """Resultado de las copias automáticas: lo escribe el servicio de copias. Siempre una sola fila."""
    __tablename__ = "estado_copias"
    __table_args__ = (CheckConstraint("id = 1"),)

    id = Column(Integer, primary_key=True, default=1)
    ultima_exitosa = Column(DateTime(timezone=True), nullable=True)
    ultimo_error_en = Column(DateTime(timezone=True), nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ConfiguracionClinica(Base):
    """Ajustes generales de la clínica: siempre una sola fila."""
    __tablename__ = "configuracion_clinica"
    __table_args__ = (CheckConstraint("id = 1"),)

    id = Column(Integer, primary_key=True, default=1)
    moneda_simbolo = Column(String(8), default="$", server_default="$", nullable=False)
    nombre_clinica = Column(String(120), default="Clínica Dental Gustavo", server_default="Clínica Dental Gustavo", nullable=False)
    logo = Column(LargeBinary, nullable=True)
    logo_tipo = Column(String(20), nullable=True)
    tema_por_defecto = Column(String(10), default="oscuro", server_default="oscuro", nullable=False)
    meses_inactividad_paciente = Column(Integer, default=3, server_default="3", nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
