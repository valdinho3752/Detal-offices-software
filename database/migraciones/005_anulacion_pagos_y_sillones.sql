-- Anulación de pagos con trazabilidad y sillones configurables.
-- Solo añade estructura y datos, y se puede ejecutar más de una vez.
-- Uso: psql -U postgres -d clinica_dental -f database/migraciones/005_anulacion_pagos_y_sillones.sql

ALTER TABLE pagos
    ADD COLUMN IF NOT EXISTS anulado BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS motivo_anulacion TEXT,
    ADD COLUMN IF NOT EXISTS fecha_anulacion TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS anulado_por_usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL;

-- Devolución en efectivo de un pago de una caja ya cerrada: no es un gasto de la clínica
ALTER TABLE egresos_caja
    ADD COLUMN IF NOT EXISTS pago_anulado_id UUID REFERENCES pagos(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS sillones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    numero INTEGER UNIQUE NOT NULL, -- Identifica al sillón en las citas; no cambia
    nombre VARCHAR(100) NOT NULL,
    especialidad VARCHAR(100),
    activo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Los tres sillones que antes estaban fijos en la agenda
INSERT INTO sillones (numero, nombre, especialidad) VALUES
    (1, 'Box 1', 'General'),
    (2, 'Box 2', 'Cirugía'),
    (3, 'Box 3', 'Ortodoncia')
ON CONFLICT (numero) DO NOTHING;

INSERT INTO permisos (modulo, accion, codigo_permiso, descripcion) VALUES
    ('CAJA', 'UPDATE', 'CAJA_ANULAR_PAGOS', 'Anular pagos de pacientes indicando el motivo')
ON CONFLICT (codigo_permiso) DO NOTHING;

INSERT INTO roles_permisos (rol_id, permiso_id)
SELECT r.id, p.id FROM roles r JOIN permisos p ON p.codigo_permiso = 'CAJA_ANULAR_PAGOS'
WHERE r.codigo = 'ADMIN'
ON CONFLICT (rol_id, permiso_id) DO NOTHING;
