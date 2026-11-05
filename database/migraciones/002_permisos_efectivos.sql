-- Los permisos ahora bloquean de verdad: agrega los que faltaban y completa los roles del sistema.
-- Solo añade datos y se puede ejecutar más de una vez. No toca los roles personalizados.
-- Uso: psql -U postgres -d clinica_dental -f database/migraciones/002_permisos_efectivos.sql

INSERT INTO permisos (modulo, accion, codigo_permiso, descripcion) VALUES
    ('HISTORIA_CLINICA', 'CREATE', 'HISTORIA_CLINICA_OBSERVAR', 'Agregar observaciones a una evolución clínica'),
    ('REPORTES', 'READ', 'REPORTES_READ', 'Consultar reportes de productividad y finanzas')
ON CONFLICT (codigo_permiso) DO NOTHING;

INSERT INTO roles_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM (VALUES
    ('DOCTOR', 'PACIENTES_READ'), ('DOCTOR', 'PACIENTES_CREATE'), ('DOCTOR', 'PACIENTES_UPDATE'), ('DOCTOR', 'ANTECEDENTES_UPDATE'),
    ('DOCTOR', 'CITAS_READ'), ('DOCTOR', 'CITAS_CREATE'), ('DOCTOR', 'CITAS_UPDATE'), ('DOCTOR', 'CITAS_SILLON'),
    ('DOCTOR', 'ODONTOGRAMA_READ'), ('DOCTOR', 'ODONTOGRAMA_CREATE'), ('DOCTOR', 'ODONTOGRAMA_UPDATE'), ('DOCTOR', 'ODONTOGRAMA_DELETE'),
    ('DOCTOR', 'TRATAMIENTOS_READ'), ('DOCTOR', 'TRATAMIENTOS_CREATE'), ('DOCTOR', 'TRATAMIENTOS_UPDATE'),
    ('DOCTOR', 'HISTORIA_CLINICA_READ'), ('DOCTOR', 'HISTORIA_CLINICA_CREATE'), ('DOCTOR', 'HISTORIA_CLINICA_UPDATE'), ('DOCTOR', 'HISTORIA_CLINICA_OBSERVAR'),
    ('DOCTOR', 'RADIOGRAFIAS_READ'), ('DOCTOR', 'RADIOGRAFIAS_CREATE'),
    ('DOCTOR', 'PROTESIS_READ'), ('DOCTOR', 'PROTESIS_CREATE'), ('DOCTOR', 'PROTESIS_UPDATE'),
    ('DOCTOR', 'ASISTENCIA_FICHAR'),
    ('ASISTENTE', 'PACIENTES_READ'), ('ASISTENTE', 'CITAS_READ'), ('ASISTENTE', 'ODONTOGRAMA_READ'), ('ASISTENTE', 'TRATAMIENTOS_READ'),
    ('ASISTENTE', 'HISTORIA_CLINICA_READ'), ('ASISTENTE', 'HISTORIA_CLINICA_OBSERVAR'),
    ('ASISTENTE', 'RADIOGRAFIAS_READ'), ('ASISTENTE', 'RADIOGRAFIAS_CREATE'), ('ASISTENTE', 'PROTESIS_READ'), ('ASISTENTE', 'ASISTENCIA_FICHAR'),
    ('RECEPCION', 'PACIENTES_READ'), ('RECEPCION', 'PACIENTES_CREATE'), ('RECEPCION', 'PACIENTES_UPDATE'),
    ('RECEPCION', 'CITAS_READ'), ('RECEPCION', 'CITAS_CREATE'), ('RECEPCION', 'CITAS_UPDATE'), ('RECEPCION', 'CITAS_SILLON'),
    ('RECEPCION', 'TRATAMIENTOS_READ'), ('RECEPCION', 'PROTESIS_READ'), ('RECEPCION', 'PROTESIS_UPDATE'),
    ('RECEPCION', 'CAJA_READ'), ('RECEPCION', 'CAJA_APERTURA'), ('RECEPCION', 'CAJA_CIERRE'), ('RECEPCION', 'CAJA_PAGOS'), ('RECEPCION', 'CAJA_EGRESOS'),
    ('RECEPCION', 'ASISTENCIA_FICHAR')
) AS asignacion(rol, permiso)
JOIN roles r ON r.codigo = asignacion.rol
JOIN permisos p ON p.codigo_permiso = asignacion.permiso
ON CONFLICT (rol_id, permiso_id) DO NOTHING;

-- El rol ADMIN conserva la lista completa, aunque el sistema ya le da acceso total
INSERT INTO roles_permisos (rol_id, permiso_id)
SELECT r.id, p.id FROM roles r CROSS JOIN permisos p WHERE r.codigo = 'ADMIN'
ON CONFLICT (rol_id, permiso_id) DO NOTHING;
