# Clínica Dental

Sistema de gestión para una clínica dental de una sola sede: pacientes, agenda, historia clínica, caja, nómina y reportes. Se instala en un equipo de la clínica y se usa desde el navegador.

## Proyecto vibecodeado

Este proyecto está **vibecodeado**: el código se generó principalmente con asistentes de IA, incluido Claude Code, a partir de las instrucciones, decisiones y revisiones funcionales del autor.

Qué implica esto:

- Las pruebas automatizadas comprueban el comportamiento, pero no sustituyen una revisión experta del código.
- El sistema no ha pasado por una auditoría de seguridad independiente.
- Maneja datos clínicos y dinero. Antes de usarlo con pacientes reales, completa las pruebas pendientes y revisa las obligaciones legales de protección de datos que apliquen a la clínica.

## Estado

| Estado de los casos de prueba | Casos |
|---|---|
| Aprobados | 531 |
| Comprobados de forma simulada; falta confirmarlos en el equipo real | 9 |
| Solo se pueden hacer a mano | 6 |
| **Total** | **546** |

Los 15 pendientes requieren otro equipo, el router, un disco externo, un corte de luz real o una semana de uso en paralelo. 13 son de prioridad alta. El detalle está en [`qa/resultados/RESUMEN.md`](qa/resultados/RESUMEN.md).

Estas cifras combinan varias ejecuciones. Falta una ejecución completa sobre la versión final, porque las pruebas de API y de operación no se repitieron después de las últimas correcciones.

## Qué incluye

- **Pacientes:** ficha, antecedentes médicos, odontograma, evolución clínica, radiografías y marcado de inactivos.
- **Agenda:** citas por sillón y doctor.
- **Tratamientos:** catálogo, presupuestos y órdenes de prótesis y laboratorio.
- **Dinero:** caja, cobros, anticipos, egresos, nómina y comisiones.
- **Personal:** usuarios, roles, permisos y control de asistencia.
- **Control:** auditoría, reportes, configuración de la clínica y cierre de sesión por inactividad.
- **Operación:** copias de seguridad diarias comprobadas y aviso al administrador si fallan.

## Tecnología

- **Backend:** Python 3.14, FastAPI, SQLAlchemy y Pydantic.
- **Base de datos:** PostgreSQL 18, con migraciones SQL en `database/migraciones/`.
- **Frontend:** React 18, Vite y Tailwind CSS.
- **Instalación:** Docker Compose, con Caddy para HTTPS.
- **Pruebas:** suites de Python para el backend; Playwright y pytest para el sistema completo.

## Instalar con Docker

Necesitas Docker Desktop y Python en el equipo. Ejecuta:

```powershell
python scripts\preparar_docker.py --levantar
```

El comando toma la zona horaria del equipo, genera las claves, muestra la contraseña inicial de `admin` e inicia el sistema en <http://localhost:8080>.

Comprueba antes que la hora de Windows sea la de la clínica, y guarda la contraseña en un lugar seguro.

> **Atención:** `docker compose down -v` borra la base de datos.

Para el uso diario, las copias de seguridad, las actualizaciones y el acceso desde otros equipos, consulta [`docs/DOCKER.md`](docs/DOCKER.md).

## Desarrollo

Crea un `.env` a partir de `.env.example`, con `ENV=development` y tus propios valores. Después crea la base de desarrollo e inicia el backend:

```powershell
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\python scripts\crear_base_limpia.py clinica_dental_dev
.\venv\Scripts\python run.py
```

Inicia el frontend en otra ventana:

```powershell
cd frontend
npm ci
npm run dev
```

## Pruebas

Las suites del backend están en `tests/`. Ejecútalas solo contra una base desechable, nunca contra una con datos reales:

```powershell
.\venv\Scripts\python tests\test_hu01.py
.\venv\Scripts\python tests\run_all_tests.py   # Solo las historias HU-01 a HU-14
```

Las pruebas del sistema completo levantan su propia instalación de Docker, separada de la real, y escriben los resultados en `qa/`:

```powershell
python -m venv qa\.venv
qa\.venv\Scripts\pip install -r qa\automatizacion\requirements.txt
qa\.venv\Scripts\python qa\automatizacion\ejecutar.py
```

Una ejecución completa tarda más de 30 minutos. Puedes usar `--reusar` para aprovechar una instalación ya en marcha, y pasar opciones a pytest después de `--`.

## Documentación

- [`docs/DOCKER.md`](docs/DOCKER.md): instalación y operación con Docker.
- [`docs/PRODUCCION.md`](docs/PRODUCCION.md): instalación en Windows sin Docker.
- [`docs/historias_de_usuario.md`](docs/historias_de_usuario.md): requisitos del sistema.
- [`database/README.md`](database/README.md): módulos y tablas de la base de datos.
- [`qa/CASOS_DE_PRUEBA.md`](qa/CASOS_DE_PRUEBA.md): los 546 casos y su estado.

## Datos y secretos

No subas nunca al repositorio los archivos `.env`, la carpeta `backups/` ni los archivos `.dump`. Contienen claves o datos clínicos, y `.gitignore` ya los excluye.
