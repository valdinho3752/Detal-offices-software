-- Nombre, logo y tema por defecto de la clínica. Se puede ejecutar más de una vez.

ALTER TABLE configuracion_clinica
    ADD COLUMN IF NOT EXISTS nombre_clinica VARCHAR(120) NOT NULL DEFAULT 'Clínica Dental Gustavo',
    ADD COLUMN IF NOT EXISTS logo BYTEA,
    ADD COLUMN IF NOT EXISTS logo_tipo VARCHAR(20),
    ADD COLUMN IF NOT EXISTS tema_por_defecto VARCHAR(10) NOT NULL DEFAULT 'oscuro';

ALTER TABLE configuracion_clinica DROP CONSTRAINT IF EXISTS configuracion_tema_valido;
ALTER TABLE configuracion_clinica ADD CONSTRAINT configuracion_tema_valido CHECK (tema_por_defecto IN ('claro', 'oscuro'));
