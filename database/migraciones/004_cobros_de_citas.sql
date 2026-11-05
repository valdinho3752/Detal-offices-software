-- Cuenta de cobro que se crea al finalizar una cita, editable hasta confirmar el pago.
-- Solo añade estructura y se puede ejecutar más de una vez.
-- Uso: psql -U postgres -d clinica_dental -f database/migraciones/004_cobros_de_citas.sql

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estado_cobro_cita_enum') THEN
        CREATE TYPE estado_cobro_cita_enum AS ENUM ('PENDIENTE', 'PAGADO', 'ANULADO');
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS cobros_cita (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cita_id UUID UNIQUE REFERENCES citas(id) ON DELETE SET NULL,
    paciente_id UUID NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    doctor_id UUID NOT NULL REFERENCES doctores(id),
    estado estado_cobro_cita_enum NOT NULL DEFAULT 'PENDIENTE',
    motivo_cierre TEXT,
    cerrado_por_usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    fecha_cierre TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS cobros_cita_lineas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cobro_id UUID NOT NULL REFERENCES cobros_cita(id) ON DELETE CASCADE,
    item_plan_id UUID REFERENCES items_plan_tratamiento(id) ON DELETE SET NULL,
    concepto VARCHAR(255) NOT NULL,
    monto NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    costo_referencia NUMERIC(12, 2)
);

ALTER TABLE pagos
    ADD COLUMN IF NOT EXISTS cobro_cita_id UUID REFERENCES cobros_cita(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_cobros_cita_estado ON cobros_cita(estado);
CREATE INDEX IF NOT EXISTS idx_cobros_cita_paciente ON cobros_cita(paciente_id);
CREATE INDEX IF NOT EXISTS idx_cobros_cita_lineas_cobro ON cobros_cita_lineas(cobro_id);
