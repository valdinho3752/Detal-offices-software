# Correr el sistema con Docker

Levanta la base de datos, el backend y la web con un solo comando. Usa una base propia, vacía y separada de la de desarrollo.

## Primera vez

Con Docker Desktop abierto:

```powershell
python scripts\preparar_docker.py --zona America/La_Paz
docker compose up --build -d
```

Indica la zona horaria real de la clínica. El primer comando genera las claves y muestra la contraseña inicial de `admin`, que también queda en `.env.docker.admin`. Guárdala en un lugar seguro.

Abre <http://localhost:8080>.

Cuando la hayas guardado, borra `.env.docker.admin`: solo se usa para crear el primer usuario.

## Uso diario

```powershell
docker compose ps                  # Estado de los servicios
docker compose logs -f backend     # Registros del backend
docker compose stop                # Detener sin perder datos
docker compose up -d               # Iniciar de nuevo
```

## Actualizar a una versión nueva

```powershell
docker compose run --rm respaldo
docker compose up --build -d
```

Las migraciones pendientes se aplican solas al arrancar.

## Copias de seguridad

```powershell
docker compose run --rm respaldo
```

Deja en `backups\` un archivo comprobado. Guárdalo fuera de este equipo: contiene datos clínicos y no está cifrado.

Para probar la restauración en una base aparte, cambia `ARCHIVO`:

```powershell
docker compose run --rm --entrypoint sh respaldo -c 'export PGPASSWORD=$POSTGRES_PASSWORD; createdb -U $POSTGRES_USER prueba_restauracion && pg_restore -U $POSTGRES_USER --no-owner --exit-on-error -d prueba_restauracion /backups/ARCHIVO.dump'
```

Solo crea la base `prueba_restauracion`; la base en uso no cambia. Para volver a probar, elimínala antes:

```powershell
docker compose exec db sh -c 'dropdb -U $POSTGRES_USER prueba_restauracion'
```

## Cambiar la zona horaria

Edita `CLINICA_TIMEZONE` en `.env.docker` y ejecuta `docker compose up -d`.

## Advertencias

- **`docker compose down -v` borra la base de datos.** Sin `-v`, los datos se conservan.
- **Solo este equipo:** la web escucha en `127.0.0.1:8080` y va por HTTP. Antes de abrirla a otros equipos hay que ponerle HTTPS.
- **Los datos no se comparten** con la base de desarrollo ni con `npm run dev`.
