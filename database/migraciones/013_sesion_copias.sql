-- Tiempo de cierre de sesión por usuario y estado de las copias automáticas. Se puede ejecutar más de una vez.

ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS minutos_inactividad INTEGER NOT NULL DEFAULT 5;

CREATE TABLE IF NOT EXISTS estado_copias (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1), -- Siempre una sola fila
    ultima_exitosa TIMESTAMP WITH TIME ZONE,
    ultimo_error_en TIMESTAMP WITH TIME ZONE,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
INSERT INTO estado_copias (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
