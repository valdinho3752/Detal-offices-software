# Instalación en producción

Guía para instalar el sistema en el equipo servidor de la clínica, con Windows, sin Docker.
La base de desarrollo no se usa aquí: producción empieza con una base nueva y vacía.

## 1. Instalar

Necesitas Python, Node.js, PostgreSQL y [Caddy](https://caddyserver.com/download).

```powershell
git clone <repositorio> C:\ClinicaDental
cd C:\ClinicaDental
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
cd frontend; npm ci; npm run build; cd ..
```

## 2. Configurar

```powershell
Copy-Item .env.example .env
.\venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Edita `.env` y reemplaza cada `CAMBIAR`. Pon la clave generada en `SECRET_KEY`, y revisa `CLINICA_TIMEZONE`.

Si algo queda inseguro, el sistema no arranca y explica el motivo. Comprueba `DEBUG`, `SECRET_KEY`,
la contraseña de PostgreSQL, `CLINICA_TIMEZONE`, `CORS_ORIGINS` y la contraseña de `admin`.

## 3. Crear la base

```powershell
.\venv\Scripts\python scripts\crear_base_limpia.py clinica_dental_prod
```

Pide la contraseña de `admin`, de al menos 12 caracteres. Guárdala en un lugar seguro.
El script se detiene si la base ya existe. El catálogo de tratamientos empieza vacío.

## 4. Iniciar

Backend:

```powershell
.\venv\Scripts\python run.py
```

HTTPS, en otra ventana y dentro de la carpeta del proyecto:

```powershell
$env:CLINICA_DIRECCION = "clinica.tudominio.com"
$env:CLINICA_RAIZ_WEB = "C:\ClinicaDental\frontend\dist"
caddy run --config deploy\Caddyfile
```

- **Con dominio público:** apunta el dominio al servidor y abre los puertos 80 y 443. Caddy obtiene el certificado solo.
- **Solo en red interna:** usa como dirección el nombre del servidor, por ejemplo `clinica.local`, y descomenta `tls internal` en `deploy/Caddyfile`.
  Después instala en cada equipo el certificado raíz que genera Caddy; si no, el navegador mostrará una advertencia.

Para que ambos arranquen con Windows, regístralos como servicios, por ejemplo con NSSM.

## 5. Programar las copias de seguridad

En PowerShell como administrador:

```powershell
.\scripts\programar_respaldo.ps1 -Carpeta "D:\RespaldosClinica" -Hora "21:00"
```

Cada copia se comprueba al crearse y se conservan las últimas 30.

**Importante:**
- Guarda las copias en otro disco y, además, fuera del local. En el mismo disco no sirven si este falla.
- Las copias contienen datos clínicos y no están cifradas: protege esa carpeta.
- Las radiografías se guardan como enlaces. La copia conserva el enlace, no la imagen; respalda aparte el lugar donde están.

## 6. Probar la restauración

Hazlo antes de empezar y luego cada cierto tiempo:

```powershell
.\venv\Scripts\python scripts\respaldar.py
.\venv\Scripts\python scripts\restaurar.py backups\ARCHIVO.dump --base clinica_prueba_restauracion
```

Compara las filas que muestra con lo esperado y revisa la base. La restauración nunca sobrescribe: siempre crea una base nueva.

**Para recuperarte de un problema real:** detén el backend, restaura en una base nueva, cambia `DB_NAME` y `DATABASE_URL` en `.env`, e inícialo de nuevo.

## 7. Actualizar a una versión nueva

```powershell
.\venv\Scripts\python scripts\respaldar.py
git pull
.\venv\Scripts\pip install -r requirements.txt
cd frontend; npm ci; npm run build; cd ..
.\venv\Scripts\python database\migrar.py
```

Después reinicia el backend.
