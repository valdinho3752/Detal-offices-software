-- Las evoluciones ya no se editan: el permiso para hacerlo deja de existir.
-- Sus asignaciones a roles y usuarios se eliminan en cascada. Se puede ejecutar más de una vez.

DELETE FROM permisos WHERE codigo_permiso = 'HISTORIA_CLINICA_UPDATE';
