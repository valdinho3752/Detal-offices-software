-- Cobros directos de consultas, que no se aplican a ningún plan, y permisos de agenda del asistente.
-- Solo añade estructura y datos, y se puede ejecutar más de una vez.
-- Uso: psql -U postgres -d clinica_dental -f database/migraciones/003_cobro_directo_y_agenda.sql

ALTER TABLE pagos
    ADD COLUMN IF NOT EXISTS es_cobro_directo BOOLEAN NOT NULL DEFAULT false;

INSERT INTO roles_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles r
JOIN permisos p ON p.codigo_permiso IN ('CITAS_UPDATE', 'CITAS_SILLON')
WHERE r.codigo = 'ASISTENTE'
ON CONFLICT (rol_id, permiso_id) DO NOTHING;
