-- Plazo sin citas para considerar inactivo a un paciente, y fecha de su última reactivación manual.
-- Se puede ejecutar más de una vez.

ALTER TABLE configuracion_clinica ADD COLUMN IF NOT EXISTS meses_inactividad_paciente INTEGER NOT NULL DEFAULT 3;
ALTER TABLE pacientes ADD COLUMN IF NOT EXISTS reactivado_en TIMESTAMP WITH TIME ZONE;
