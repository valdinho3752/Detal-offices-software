-- Una sola caja abierta, control de sesiones y contraseñas, y marcajes anulados.
-- Se puede ejecutar más de una vez. Falla con un aviso si ya hay más de una caja abierta: ciérralas antes.

CREATE UNIQUE INDEX IF NOT EXISTS caja_unica_abierta ON cajas_sesiones ((1)) WHERE estado = 'ABIERTA';

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS version_sesion INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS debe_cambiar_contrasena BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE registro_asistencia
    ADD COLUMN IF NOT EXISTS anulado BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS motivo_anulacion TEXT,
    ADD COLUMN IF NOT EXISTS anulado_por_usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL;
