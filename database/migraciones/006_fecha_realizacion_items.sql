-- Fecha en que se realizó cada tratamiento, para filtrar por periodo los reportes de demanda.
-- Solo añade la columna y la completa en los ya realizados; se puede ejecutar más de una vez.
-- Uso: psql -U postgres -d clinica_dental -f database/migraciones/006_fecha_realizacion_items.sql

ALTER TABLE items_plan_tratamiento
    ADD COLUMN IF NOT EXISTS fecha_realizacion TIMESTAMP WITH TIME ZONE;

-- La cita finalizada es la mejor referencia; una cita puede incluir ítems en sus notas.
-- Sin cita ni evolución, la fecha de creación es el único dato disponible.
UPDATE items_plan_tratamiento i
SET fecha_realizacion = COALESCE(
    (SELECT MIN(c.fecha_inicio_programada) FROM citas c
     WHERE c.estado = 'FINALIZADA'
       AND (c.item_plan_id = i.id OR c.notas_adicionales ILIKE '%' || i.id::text || '%')),
    (SELECT MIN(v.fecha_hora) FROM visitas_evolucion v WHERE v.item_plan_id = i.id),
    i.created_at
)
WHERE i.estado = 'COMPLETADO' AND i.fecha_realizacion IS NULL;
