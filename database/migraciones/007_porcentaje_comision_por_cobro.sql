-- Cada cobro conserva el porcentaje de comisión vigente al registrarse: cambiar el contrato no altera el pasado.
-- Los cobros existentes toman el porcentaje actual, así sus comisiones no cambian. Se puede ejecutar más de una vez.

ALTER TABLE pagos
    ADD COLUMN IF NOT EXISTS porcentaje_comision NUMERIC(5, 2);

UPDATE pagos p
SET porcentaje_comision = COALESCE(
    (SELECT c.porcentaje_comision
     FROM doctores d
     JOIN contratos_remuneracion c ON c.usuario_id = d.usuario_id
     WHERE d.id = p.doctor_comision_id),
    0
)
WHERE p.porcentaje_comision IS NULL;

ALTER TABLE pagos
    ALTER COLUMN porcentaje_comision SET DEFAULT 0,
    ALTER COLUMN porcentaje_comision SET NOT NULL;
