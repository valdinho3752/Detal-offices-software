import uuid
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Date, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.models.enums import TipoEstudioImagenEnum

class RadiografiaEstudio(Base):
    __tablename__ = "radiografias_estudios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paciente_id = Column(UUID(as_uuid=True), ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False)
    subido_por_usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    visita_id = Column(UUID(as_uuid=True), ForeignKey("visitas_evolucion.id", ondelete="SET NULL"), nullable=True)
    pieza_fdi = Column(Integer, nullable=True)
    tipo_estudio = Column(ENUM(TipoEstudioImagenEnum, name="tipo_estudio_imagen_enum", create_type=False), nullable=False)
    titulo = Column(String(200), nullable=False)
    archivo_url = Column(String(500), nullable=False)
    mime_type = Column(String(100), default="image/jpeg", nullable=False)
    tamano_bytes = Column(BigInteger, nullable=True)
    informe_diagnostico = Column(Text, nullable=True)
    fecha_toma = Column(Date, default=func.current_date(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    paciente = relationship("Paciente", back_populates="radiografias")
    usuario_subio = relationship("Usuario")
    visita = relationship("VisitaEvolucion", back_populates="radiografias")
