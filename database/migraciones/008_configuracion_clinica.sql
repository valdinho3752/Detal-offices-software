-- Configuración general de la clínica, con una sola fila. Empieza con la moneda de la clínica.
-- Se puede ejecutar más de una vez.

CREATE TABLE IF NOT EXISTS configuracion_clinica (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    moneda_simbolo VARCHAR(8) NOT NULL DEFAULT '$',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

INSERT INTO configuracion_clinica (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
