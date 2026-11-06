"""Instalación local: contenedores, HTTPS, copias de seguridad y seguridad general."""
import re
import subprocess
import sys
from uuid import uuid4

import pytest
from apoyo import BASE, CLAVE_ADMIN, RAIZ, RESPALDOS, dc, peticion_directa, sql

caso = pytest.mark.caso


@caso("OPE-02")
def test_servicios_en_marcha():
    estados = dc("ps", "-a", "--format", "{{.Service}}={{.Status}}")
    for servicio in ("backend=Up", "db=Up", "web=Up", "https=Up", "respaldos=Up"):
        assert servicio in estados, estados
    assert re.search(r"migraciones=Exited \(0\)", estados), estados


@caso("OPE-03")
def test_puertos_publicados():
    for servicio, puerto in (("db", 5432), ("backend", 8000)):
        contenedor = f"clinica-qa-{servicio}-1"
        ligaduras = subprocess.run(["docker", "inspect", contenedor, "--format", "{{json .HostConfig.PortBindings}}"], capture_output=True, text=True).stdout.strip()
        assert ligaduras == "{}", f"{servicio}: {ligaduras}"
    web = subprocess.run(["docker", "inspect", "clinica-qa-web-1", "--format", "{{json .HostConfig.PortBindings}}"], capture_output=True, text=True).stdout
    assert '"HostIp":"127.0.0.1"' in web


@caso("OPE-04")
def test_documentacion_no_disponible():
    orden = "import urllib.request,urllib.error\nfor r in ('docs','redoc','openapi.json'):\n    try:\n        print(r, urllib.request.urlopen('http://localhost:8000/'+r).status)\n    except urllib.error.HTTPError as e:\n        print(r, e.code)"
    salida = dc("exec", "-T", "backend", "python", "-c", orden)
    assert salida.split() == ["docs", "404", "redoc", "404", "openapi.json", "404"], salida


@caso("SEG-11")
def test_dependencias_sin_vulnerabilidades():
    npm = subprocess.run("npm audit --omit=dev --audit-level=high", shell=True, cwd=RAIZ / "frontend", capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert npm.returncode == 0, npm.stdout[-600:]
    pip = subprocess.run([sys.executable, "-m", "pip_audit", "-r", str(RAIZ / "requirements.txt"), "--progress-spinner", "off"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert pip.returncode == 0, (pip.stdout + pip.stderr)[-800:]


@caso("OPE-05")
def test_no_arranca_con_configuracion_insegura():
    salida = dc("run", "--rm", "--no-deps", "-e", "SECRET_KEY=corta", "backend", "python", "-c", "import app.main", comprobar=False)
    assert "No se puede arrancar en producción" in salida and "SECRET_KEY" in salida
    salida = dc("run", "--rm", "--no-deps", "-e", "DEBUG=True", "backend", "python", "-c", "import app.main", comprobar=False)
    assert "DEBUG debe ser False" in salida
    salida = dc("run", "--rm", "--no-deps", "-e", "CLINICA_TIMEZONE=", "backend", "python", "-c", "import app.main", comprobar=False)
    assert "CLINICA_TIMEZONE" in salida


# Sin caso propio: comprobación adicional
def test_copia_automatica():
    copias = sorted(RESPALDOS.glob("clinica_auto_*.dump"))
    assert copias and copias[-1].stat().st_size > 10000, [c.name for c in copias]
    assert "Copia creada y comprobada" in dc("logs", "respaldos")


@caso("OPE-10", "OPE-11")
def test_restaurar_copia(fab, api):
    api.put("/configuracion/", {"nombre_clinica": "Antes de la copia"})
    nombre_doc = f"Restaurar{uuid4().hex[:6]}"
    paciente = fab.paciente(nombres=nombre_doc)
    salida = dc("run", "--rm", "respaldo")
    assert "Copia creada y comprobada" in salida
    archivo = sorted(RESPALDOS.glob("clinica_docker_*.dump"), key=lambda a: a.stat().st_mtime)[-1]
    consulta = "select (select count(*) from pacientes)||'/'||(select count(*) from citas)||'/'||(select count(*) from pagos)||'/'||(select count(*) from visitas_evolucion)"
    original = sql(consulta)
    base = f"qa_rest_{uuid4().hex[:6]}"
    orden = (
        f'export PGPASSWORD=$POSTGRES_PASSWORD; createdb -U $POSTGRES_USER {base} && '
        f'pg_restore -U $POSTGRES_USER --no-owner --exit-on-error -d {base} /backups/{archivo.name} && '
        f'psql -U $POSTGRES_USER -d {base} -Atc "{consulta}" && '
        f'psql -U $POSTGRES_USER -d {base} -Atc "select nombre_clinica from configuracion_clinica" && '
        f'psql -U $POSTGRES_USER -d {base} -Atc "select count(*) from pacientes where nombres = \'{nombre_doc}\'"'
    )
    salida = dc("exec", "-T", "respaldos", "sh", "-c", orden)
    lineas = [l for l in salida.strip().splitlines() if l.strip()]
    assert lineas[-3] == original, salida[-300:]
    assert lineas[-2] == "Antes de la copia" and lineas[-1] == "1"
    api.put("/configuracion/", {"nombre_clinica": "Clínica Dental"})
    assert paciente["id"]


# Sin caso propio: comprobación adicional
def test_migraciones_al_dia():
    registradas = sql("select count(*) from migraciones_aplicadas")
    archivos = len(list((RAIZ / "database" / "migraciones").glob("*.sql")))
    assert int(registradas) == archivos
    dc("up", "-d", "--no-deps", "migraciones")
    assert "ya estaba al día" in dc("logs", "--tail", "1", "migraciones")


@caso("OPE-14")
def test_reinicio_del_backend(api):
    assert api.get("/auth/me").status == 200
    dc("restart", "backend")
    dc("up", "-d", "--wait", "backend")
    assert api.get("/auth/me").status == 200, "Las sesiones siguen válidas"


@caso("OPE-16", "RED-01")
def test_https_y_zona_horaria(fab, api):
    assert BASE.startswith("https://")
    assert api.get("/caja/estado").ok
    p = fab.paciente()["id"]
    from apoyo import ZONA, ahora_clinica
    cita = fab.cita(p, ahora_clinica().strftime("%Y-%m-%d"), "03:00", "03:30", box=3)
    assert ZONA and api.get("/caja/estado").json()["fecha_servidor"] == ahora_clinica().strftime("%Y-%m-%d")
    if cita.status == 201:
        api.delete(f"/citas/{cita.json()['id']}")


@caso("RED-04", "RED-05")
def test_redireccion_y_cabeceras(solicitudes):
    respuesta = solicitudes.get("http://localhost:8180/", max_redirects=0)
    assert respuesta.status in (301, 302, 308) and respuesta.headers.get("location", "").startswith("https://")
    cabeceras = solicitudes.get(f"{BASE}/").headers
    assert "max-age" in cabeceras.get("strict-transport-security", "")
    assert cabeceras.get("x-content-type-options") == "nosniff" and cabeceras.get("x-frame-options") == "DENY"
    assert "server" not in cabeceras


@caso("SEG-01")
def test_inyeccion_en_busquedas(api):
    for intento in ("' OR '1'='1", "'; DROP TABLE pacientes; --", "%' --"):
        res = api.get("/pacientes/", buscar=intento, busqueda=intento, q=intento, search=intento)
        assert res.status == 200, intento
    assert int(sql("select count(*) from pacientes")) > 0


@caso("SEG-03")
def test_acceso_a_datos_de_otro(fab):
    otro = fab.usuario("RECEPCION")
    doc = fab.usuario("DOCTOR")
    assert doc.api.get(f"/empleados/liquidacion/{otro.id}").status == 403
    assert otro.api.get(f"/usuarios/{doc.id}").status == 403


@caso("SEG-04")
def test_campos_no_previstos(fab, api):
    p = fab.paciente()["id"]
    assert api.post("/caja/pagos", {"paciente_id": p, "monto": 1, "metodo_pago": "OTRO", "es_cobro_directo": True, "observaciones": "x", "anulado": True}).status == 422
    assert api.post("/empleados/pagos", {"usuario_empleado_id": fab.usuario().id, "tipo_pago": "BONO", "monto_neto_pagado": 1, "metodo_pago": "OTRO", "nada": 1}).status == 422


@caso("SEG-06")
def test_codigo_publicado_sin_secretos(solicitudes):
    html = solicitudes.get(f"{BASE}/").text()
    for ruta in re.findall(r'src="(/assets/[^"]+\.js)"', html):
        codigo = solicitudes.get(BASE + ruta).text()
        assert CLAVE_ADMIN not in codigo and "admin123" not in codigo and "DoctorPassword" not in codigo


@caso("SEG-07")
def test_imagen_del_backend():
    assert dc("exec", "-T", "backend", "id", "-u").strip() != "0"
    assert dc("exec", "-T", "web", "id", "-u").strip() != "0"
    listado = dc("exec", "-T", "backend", "ls", "-a", "/app")
    assert ".env" not in listado and "tests" not in listado and "backups" not in listado


@caso("SEG-08")
def test_repositorio_sin_secretos():
    versionados = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8").stdout.splitlines()
    assert not {".env", ".env.docker", ".env.docker.admin"} & set(versionados)
    assert not [a for a in versionados if a.endswith(".dump") or a.startswith("backups/")]


@caso("SEG-12")
def test_no_se_falsifica_la_ip_para_saltar_el_limite(fab):
    """Con HTTPS, la cabecera X-Forwarded-For del cliente no debe permitir evadir el bloqueo."""
    u = fab.usuario()
    formulario = f"username={u.alias}&password=Incorrecta1".encode()
    import ssl
    import urllib.error
    import urllib.request
    contexto = ssl.create_default_context()
    contexto.check_hostname = False
    contexto.verify_mode = ssl.CERT_NONE
    estados = []
    for indice in range(8):
        solicitud = urllib.request.Request(f"{BASE}/api/v1/auth/login", data=formulario, method="POST", headers={
            "Content-Type": "application/x-www-form-urlencoded", "X-Forwarded-For": f"10.9.8.{indice}", "X-Real-IP": f"10.9.8.{indice}",
        })
        try:
            urllib.request.urlopen(solicitud, context=contexto, timeout=30)
            estados.append(200)
        except urllib.error.HTTPError as error:
            estados.append(error.code)
    assert estados[5:] == [429, 429, 429], estados
