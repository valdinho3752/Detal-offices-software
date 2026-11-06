# Correr el sistema con Docker

Levanta la base de datos, el backend y la web con un solo comando. Usa una base propia, vacía y separada de la de desarrollo.

## Primera vez

Con Docker Desktop abierto:

```powershell
python scripts\preparar_docker.py --levantar
```

Toma la zona horaria de este equipo, genera las claves, muestra la contraseña inicial de `admin` (que también queda en `.env.docker.admin`), construye e inicia el sistema. Guarda la contraseña en un lugar seguro.

Revisa que la hora de Windows de este equipo sea la de la clínica: todos los equipos que abran el sistema mostrarán esa zona.

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
python scripts\preparar_docker.py --levantar
```

Las claves no cambian; solo se actualiza la zona horaria si la del equipo cambió. Docker no puede leer la zona de Windows por sí mismo: con `docker compose up --build -d` directo se usa la última zona guardada.

Las migraciones pendientes se aplican solas al arrancar.

## Copias de seguridad

El servicio `respaldos` crea una copia comprobada cada día desde las 21:00, hora de la clínica, y conserva las 30 más recientes en `backups\`. Si el equipo estaba apagado a esa hora, la crea al encender, en cuanto pasen 24 horas desde la anterior. Si una copia falla o lleva más de 26 horas sin hacerse, el administrador ve un aviso en todas las pantallas. Para ver el detalle:

```powershell
docker compose logs respaldos
```

Puedes cambiar la carpeta, la hora y la cantidad antes de iniciar el sistema:

```powershell
$env:CLINICA_RESPALDOS = "D:\RespaldosClinica"
$env:RESPALDO_HORA = "20"
$env:RESPALDO_CONSERVAR = "60"
docker compose up -d
```

**Importante:** una copia en el mismo disco no protege si este falla. Usa otro disco o una carpeta sincronizada fuera del local. Las copias contienen datos clínicos y no están cifradas.

Para crear una copia en cualquier momento:

```powershell
docker compose run --rm respaldo
```

Para probar la restauración en una base aparte, cambia `ARCHIVO`:

```powershell
docker compose run --rm --entrypoint sh respaldo -c 'export PGPASSWORD=$POSTGRES_PASSWORD; createdb -U $POSTGRES_USER prueba_restauracion && pg_restore -U $POSTGRES_USER --no-owner --exit-on-error -d prueba_restauracion /backups/ARCHIVO.dump'
```

Solo crea la base `prueba_restauracion`; la base en uso no cambia. Para volver a probar, elimínala antes:

```powershell
docker compose exec db sh -c 'dropdb -U $POSTGRES_USER prueba_restauracion'
```

## Abrir el sistema a otros equipos con HTTPS

Edita `.env.docker` e inicia con el perfil `https`:

- **Dominio público:** `CLINICA_DIRECCION=clinica.tudominio.com` y `CLINICA_TLS=` vacío. Apunta el dominio al servidor y abre los puertos 80 y 443. El certificado se obtiene solo.
- **Red interna:** `CLINICA_DIRECCION=clinica.local` y `CLINICA_TLS=tls internal`. Cada equipo debe poder resolver ese nombre. Para que el navegador no muestre una advertencia, instala en cada uno el certificado raíz:

```powershell
docker compose cp https:/data/caddy/pki/authorities/local/root.crt certificado-clinica.crt
```

```powershell
docker compose --profile https up -d
```

## Recuperar el acceso del administrador

Si se pierde la contraseña de `admin`:

```powershell
docker compose run --rm -it migraciones python scripts/restablecer_admin.py
```

Pide la contraseña nueva, reactiva la cuenta y cierra sus sesiones anteriores.

## Cambiar la zona horaria

Cambia la zona de Windows y ejecuta `python scripts\preparar_docker.py --levantar`. Para usar otra distinta a la del equipo, añade `--zona America/La_Paz`. Volver a ejecutar el comando sin `--zona` la reemplaza por la del equipo.

## Advertencias

- **`docker compose down -v` borra la base de datos.** Sin `-v`, los datos se conservan.
- **Sin el perfil `https`:** la web solo escucha en `127.0.0.1:8080`, por HTTP.
- **Primer ingreso:** quien recibe una cuenta nueva o una contraseña restablecida debe cambiarla al entrar.
- **Los datos no se comparten** con la base de desarrollo ni con `npm run dev`.
