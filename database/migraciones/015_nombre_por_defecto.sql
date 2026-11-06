-- El nombre por defecto pasa a ser genérico. Un nombre elegido por la clínica no se toca.
-- Se puede ejecutar más de una vez.

ALTER TABLE configuracion_clinica ALTER COLUMN nombre_clinica SET DEFAULT 'Clínica Dental';
UPDATE configuracion_clinica SET nombre_clinica = 'Clínica Dental' WHERE nombre_clinica = 'Clínica Dental Gustavo';
