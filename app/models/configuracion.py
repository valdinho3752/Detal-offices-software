from sqlalchemy import CheckConstraint, Column, DateTime, Integer, String
from sqlalchemy.sql import func
from app.database import Base

class ConfiguracionClinica(Base):
    """Ajustes generales de la clínica: siempre una sola fila."""
    __tablename__ = "configuracion_clinica"
    __table_args__ = (CheckConstraint("id = 1"),)

    id = Column(Integer, primary_key=True, default=1)
    moneda_simbolo = Column(String(8), default="$", server_default="$", nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
