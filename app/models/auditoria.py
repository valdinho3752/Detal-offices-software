import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.models.enums import AuditoriaAccionEnum

class AuditoriaLog(Base):
    __tablename__ = "auditoria_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    tabla_afectada = Column(String(100), nullable=False)
    registro_id = Column(UUID(as_uuid=True), nullable=True)
    accion = Column(ENUM(AuditoriaAccionEnum, name="auditoria_accion_enum", create_type=False), nullable=False)
    seccion_consultada = Column(String(100), nullable=True)
    datos_previos = Column(JSONB, nullable=True)
    datos_nuevos = Column(JSONB, nullable=True)
    ip_origen = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    fecha_hora = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    usuario = relationship("Usuario", back_populates="auditorias")

    @property
    def usuario_nombre(self) -> str:
        return f"{self.usuario.nombre} {self.usuario.apellido}" if self.usuario else None
