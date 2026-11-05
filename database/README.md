# Base de Datos Relacional - Clínica Dental Gustavo

Este directorio contiene la definición completa de la base de datos relacional para el sistema dental.

## Archivos
- `schema.sql`: Script DDL para **PostgreSQL 14+** con todas las tablas, llaves primarias/foráneas, enums, triggers automáticos e índices de alto rendimiento.

---

## Módulos del Sistema

| # | Módulo | Tablas Principales | Propósito |
|---|---|---|---|
| 1 | **Seguridad y RBAC** | `roles`, `permisos`, `roles_permisos`, `usuarios`, `usuarios_permisos_especiales` | Control de acceso por rol y excepciones individuales. |
| 2 | **Personal y Asistencia** | `doctores`, `asistentes`, `registro_asistencia`, `contratos_remuneracion` | Perfiles, reloj de control de entradas/salidas/descansos y salarios/comisiones. |
| 3 | **Auditoría Global** | `auditoria_logs` | Registro de cambios y visualizaciones (`VIEW`) para cumplimiento médico y de privacidad. |
| 4 | **Pacientes y Ficha Médica** | `pacientes`, `antecedentes_medicos` | Filiación, emergencias y anamnesis médica completa. |
| 5 | **Tooth Chart / Odontograma** | `odontogramas`, `piezas_dentales`, `hallazgos_superficie` | Odontograma interactivo FDI (adulto e infantil), 5 caras por diente y colores por patología. |
| 6 | **Tratamientos y Secuencia** | `catalogo_tratamientos`, `planes_tratamiento`, `items_plan_tratamiento` | Catálogo de precios, presupuestos paso a paso y tratamiento para la próxima sesión. |
| 7 | **Citas y Tiempos de Sillón** | `citas` | Agenda médica, tiempos reales de atención en sillón y cálculo automático de minutos. |
| 8 | **Historia Clínica / Evolución** | `visitas_evolucion` | Hoja de evolución diaria, doctor, asistente, procedimientos y recetas. |
| 9 | **Radiografías e Imágenes** | `radiografias_estudios` | Panorámicas, periapicales, CBCT 3D y fotografías clínicas con visor. |
| 10 | **Órdenes de Prótesis / Lab** | `ordenes_laboratorio_protesis` | Control de trabajos de laboratorio, costos, color Vita, fechas de entrega y alertas. |
| 11 | **Caja y Finanzas en Vivo** | `cajas_sesiones`, `pagos`, `egresos_caja`, `pagos_empleados` | Saldo de pacientes, cobros, gastos físicos, adelantos de sueldo y cálculo del efectivo en gaveta al instante. |

---

## Cómo Ejecutar el Script

### Opción A: Mediante Docker (Recomendado para desarrollo)
```bash
docker run --name clinica-postgres -e POSTGRES_PASSWORD=secret -e POSTGRES_DB=clinica_dental -p 5432:5432 -d postgres:16-alpine
docker exec -i clinica-postgres psql -U postgres -d clinica_dental < database/schema.sql
```

### Opción B: En servidor PostgreSQL local o VPS
```bash
psql -U postgres -d clinica_dental -f database/schema.sql
```

### Producción
Usa `scripts/crear_base_limpia.py` para crear la base y `database/migrar.py` para actualizarla. Consulta `docs/PRODUCCION.md`.
