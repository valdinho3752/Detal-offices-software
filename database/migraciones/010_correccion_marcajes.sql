-- Marcajes agregados por el administrador. Se identifican como corrección y conservan su motivo.
-- Se puede ejecutar más de una vez.

ALTER TABLE registro_asistencia
    ADD COLUMN IF NOT EXISTS es_correccion BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS motivo_correccion TEXT,
    ADD COLUMN IF NOT EXISTS corregido_por_usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL;
