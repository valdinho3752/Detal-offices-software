-- Evolución creada al finalizar una cita y observaciones de solo agregar.
-- Solo añade estructura y se puede ejecutar más de una vez.
-- Uso: psql -U postgres -d clinica_dental -f database/migraciones/001_evolucion_automatica.sql

ALTER TABLE visitas_evolucion
    ADD COLUMN IF NOT EXISTS generada_automaticamente BOOLEAN NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS observaciones_evolucion (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    visita_id UUID NOT NULL REFERENCES visitas_evolucion(id) ON DELETE CASCADE,
    autor_usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    rol_autor VARCHAR(50) NOT NULL,
    texto TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_observaciones_visita ON observaciones_evolucion(visita_id, created_at);
