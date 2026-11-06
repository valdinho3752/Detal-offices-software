"""
Pruebas que reinician servicios, cargan mucho volumen o esperan en tiempo real.
Se ejecutan al final: el archivo se llama así a propósito, y no deben mezclarse con las demás.
"""
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import threading
import time
import urllib.parse
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import timedelta
from hashlib import sha256
from hmac import new as hmac_new
from pathlib import Path
from uuid import uuid4

import pytest
from apoyo import BASE, CLAVE_ADMIN, ENTORNO, PROYECTO, RAIZ, RESPALDOS, ahora_clinica, dc, peticion_directa, sql, _valor_env

caso = pytest.mark.caso
VERSION_ANTERIOR = "7e1f7df"  # Primera versión instalable con Docker


# ---------------- Otro equipo de la red ----------------

SCRIPT_CLIENTE = r"""
import http.client, json, socket, ssl, sys
metodo, ruta, cuerpo, tipo, token = json.loads(sys.argv[1])
class Conexion(http.client.HTTPSConnection):
    def connect(self):
        self.sock = ssl._create_unverified_context().wrap_socket(socket.create_connection(("https", 443)), server_hostname="localhost")
c = Conexion("localhost")
cabeceras = {"Content-Type": tipo}
if token:
    cabeceras["Authorization"] = "Bearer " + token
c.request(metodo, "/api/v1" + ruta, cuerpo, cabeceras)
r = c.getresponse()
print(json.dumps({"status": r.status, "cuerpo": r.read().decode()}))
"""


def desde_otro_equipo(metodo, ruta, cuerpo=None, tipo="application/json", token=None):
    """El contenedor del backend hace de otro equipo: entra por HTTPS como cualquiera, con otra dirección."""
    salida = dc("exec", "-T", "backend", "python", "-c", SCRIPT_CLIENTE, json.dumps([metodo, ruta, cuerpo, tipo, token]))
    return json.loads(salida.strip().splitlines()[-1])


def entrar_desde_otro_equipo(usuario, clave):
    return desde_otro_equipo("POST", "/auth/login", urllib.parse.urlencode({"username": usuario, "password": clave}), "application/x-www-form-urlencoded")


def bloquear(sin_sesion, alias):
    for _ in range(5):
        assert sin_sesion.login(alias, "Incorrecta1").status == 401
    assert sin_sesion.login(alias, "Incorrecta1").status == 429


@caso("ACC-10")
def test_bloqueo_solo_afecta_a_un_equipo(fab, sin_sesion):
    u = fab.usuario()
    bloquear(sin_sesion, u.alias)
    assert sin_sesion.login(u.alias, u.clave).status == 429, "En este equipo sigue bloqueado, aun con la clave correcta"
    assert entrar_desde_otro_equipo(u.alias, u.clave)["status"] == 200, "Desde el otro equipo sí puede entrar"


@caso("ACC-11", "ACC-12")
def test_muchos_usuarios_falsos_y_reinicio(fab, sin_sesion):
    u = fab.usuario()
    v = fab.usuario()
    for indice in range(50):
        estado = entrar_desde_otro_equipo(f"falso_{uuid4().hex[:6]}_{indice}", "Incorrecta1")["status"]
        assert estado == 401, (indice, estado)
    assert entrar_desde_otro_equipo(u.alias, u.clave)["status"] == 429, "El equipo queda frenado, también para usuarios válidos"
    assert sin_sesion.login(u.alias, u.clave).status == 200, "Los demás equipos no se ven afectados"
    bloquear(sin_sesion, v.alias)
    dc("restart", "backend")
    dc("up", "-d", "--wait", "backend")
    assert sin_sesion.login(v.alias, v.clave).status == 200, "El bloqueo desaparece, porque se guarda en memoria"
    assert entrar_desde_otro_equipo(u.alias, u.clave)["status"] == 200


@caso("ASI-19")
def test_ip_real_del_otro_equipo(fab):
    u = fab.usuario()
    token = json.loads(entrar_desde_otro_equipo(u.alias, u.clave)["cuerpo"])["access_token"]
    respuesta = desde_otro_equipo("POST", "/auth/fichar", json.dumps({"tipo_evento": "ENTRADA"}), token=token)
    assert respuesta["status"] in (200, 201), respuesta
    registrada = json.loads(respuesta["cuerpo"])["ip_registro"]
    propia = dc("exec", "-T", "backend", "python", "-c", "import socket; print(socket.gethostbyname(socket.gethostname()))").strip().splitlines()[-1]
    assert registrada == propia, (registrada, propia)


def _firmar_token(token, **cambios):
    def b64(datos):
        return urlsafe_b64encode(datos).rstrip(b"=").decode()

    cabecera, cuerpo, _ = token.split(".")
    datos = json.loads(urlsafe_b64decode(cuerpo + "=" * (-len(cuerpo) % 4)))
    datos.update(cambios)
    nuevo = f"{cabecera}.{b64(json.dumps(datos).encode())}"
    firma = hmac_new(_valor_env(".env.docker", "SECRET_KEY").encode(), nuevo.encode(), sha256).digest()
    return f"{nuevo}.{b64(firma)}"


@caso("ACC-18")
def test_sesion_vence_a_las_ocho_horas(fab, api, abrir):
    u = fab.usuario()
    token = u.api.token
    cuerpo = token.split(".")[1]
    expira = json.loads(urlsafe_b64decode(cuerpo + "=" * (-len(cuerpo) % 4)))["exp"]
    assert abs(expira - time.time() - 8 * 3600) < 120, "Se emite por 8 horas"
    # El mismo token, firmado como corresponde, ocho horas después
    vencido = _firmar_token(token, exp=int(time.time()) - 60)
    assert api.como(vencido).get("/auth/me").status == 401
    p = abrir(u.alias, u.clave)
    p.evaluate("(t) => localStorage.setItem('token', t)", vencido)
    p.goto(f"{BASE}/pacientes")
    p.wait_for_url(f"{BASE}/login")


# ---------------- Decisiones pendientes: se comprueba cómo funciona hoy ----------------

@caso("AGE-38")
def test_citas_en_fechas_pasadas_se_permiten(fab):
    res = fab.cita(fab.paciente()["id"], "2020-03-03", "09:00", "09:30", doctor=fab.usuario("DOCTOR").doctor_id)
    assert res.status == 201, res.text


@caso("CAJ-23")
def test_ningun_cobro_sin_caja_abierta(fab, api):
    pid = fab.paciente()["id"]
    plan = fab.plan(pid)
    item = fab.item(plan, fab.tratamiento(50)["id"], 50, pieza_fdi=11, superficie="OCLUSAL")
    assert api.put(f"/tratamientos/planes/{plan}", {"estado": "APROBADO"}).ok
    fab.caja()
    cita = fab.cita(pid, item_plan_id=item["id"]).json()
    assert api.put(f"/citas/{cita['id']}", {"estado": "FINALIZADA"}).ok
    cuenta = next(c for c in api.get("/cobros-cita/").json() if c["cita_id"] == cita["id"])
    fab.cerrar_caja()
    try:
        for metodo in ("EFECTIVO", "TRANSFERENCIA", "TARJETA_DEBITO", "TARJETA_CREDITO", "OTRO"):
            res = api.post("/caja/pagos", {"paciente_id": pid, "monto": 10, "metodo_pago": metodo, "es_cobro_directo": True, "observaciones": "Consulta"})
            assert res.status == 400 and "caja abierta" in res.detalle, (metodo, res.text)
        res = api.post(f"/cobros-cita/{cuenta['id']}/confirmar", {"metodo_pago": "TRANSFERENCIA", "doctor_comision_id": fab.doctor})
        assert res.status == 400 and "caja abierta" in res.detalle, res.text
    finally:
        fab.caja()
    # Con la caja abierta, la transferencia queda en el turno sin tocar el efectivo
    gaveta = fab.gaveta()
    pago = fab.cobro_directo(pid, 10, "TRANSFERENCIA")
    assert pago["caja_sesion_id"] and fab.gaveta() == gaveta


# Sin saldo por cobrar, un empleado desactivado sale de la lista
def test_empleado_desactivado_sin_saldo_desaparece(fab, api):
    rec = fab.usuario("RECEPCION", salario_base=1000)
    assert api.put(f"/usuarios/{rec.id}", {"activo": False}).ok
    assert rec.id not in {e["usuario_id"] for e in api.get("/empleados/personal").json()}


# ---------------- Copias automáticas ----------------

def _esperar(condicion, segundos=45, mensaje=""):
    limite = time.time() + segundos
    while time.time() < limite:
        if condicion():
            return
        time.sleep(1)
    raise AssertionError(mensaje or "Tiempo agotado")


@caso("OPE-08", "OPE-09")
def test_copia_al_encender_y_conservacion():
    antiguas = []
    for indice in range(35):
        falsa = RESPALDOS / f"clinica_auto_201001{indice % 28 + 1:02d}_0{indice % 10}{indice:02d}00.dump"
        falsa.write_bytes(b"antigua")
        os.utime(falsa, (time.time() - 86400 * (100 + indice), time.time() - 86400 * (100 + indice)))
        antiguas.append(falsa)
    # Sin la copia de hoy, como si el equipo hubiera estado apagado a la hora programada
    hoy = ahora_clinica().strftime("%Y%m%d")
    for copia in RESPALDOS.glob(f"clinica_auto_{hoy}_*.dump"):
        copia.unlink()
    dc("restart", "respaldos")
    _esperar(lambda: list(RESPALDOS.glob(f"clinica_auto_{hoy}_*.dump")), mensaje="No se recuperó la copia del día")
    copia = next(RESPALDOS.glob(f"clinica_auto_{hoy}_*.dump"))
    assert copia.stat().st_size > 10000
    _esperar(lambda: len(list(RESPALDOS.glob("clinica_auto_*.dump"))) <= 30, 15, "No conservó solo las últimas 30")
    assert copia.exists(), "Conserva la más reciente"
    assert not (RESPALDOS / antiguas[-1].name).exists(), "Elimina las más antiguas"
    for falsa in RESPALDOS.glob("clinica_auto_2010*.dump"):
        falsa.unlink()


def _ciclo_de_copias(hora=24):
    """Una vuelta del servicio de copias, antes de la hora programada."""
    orden = "timeout 12 sh /respaldo_diario.sh; true"
    return dc("run", "--rm", "--no-deps", "-T", "-e", f"RESPALDO_HORA={hora}", "--entrypoint", "sh", "respaldos", "-c", orden)


@caso("OPE-08")
def test_equipo_apagado_antes_de_la_hora_programada():
    """Si el equipo se apaga cada noche antes de las 21:00, igual debe haber una copia diaria."""
    hoy = ahora_clinica().strftime("%Y%m%d")
    for copia in RESPALDOS.glob("clinica_auto_*.dump"):
        copia.unlink()
    anterior = RESPALDOS / "clinica_auto_20100101_210000.dump"
    anterior.write_bytes(b"anterior")

    # Hace menos de 24 horas: todavía no toca
    os.utime(anterior, (time.time() - 3600, time.time() - 3600))
    _ciclo_de_copias()
    assert not list(RESPALDOS.glob(f"clinica_auto_{hoy}_*.dump"))

    # Hace más de 24 horas: se crea al encender, aunque aún no sea la hora
    os.utime(anterior, (time.time() - 90000, time.time() - 90000))
    salida = _ciclo_de_copias()
    assert "Copia creada y comprobada" in salida, salida[-300:]
    assert list(RESPALDOS.glob(f"clinica_auto_{hoy}_*.dump"))
    anterior.unlink()


@caso("OPE-12", "OPE-15")
def test_copia_sin_disco_deja_error_y_el_sistema_sigue(solicitudes, api, fab, abrir, como_admin):
    orden = (
        "sed 's#^CARPETA=.*#CARPETA=/disco_desconectado#' /respaldo_diario.sh > /tmp/r.sh; "
        "timeout 15 sh /tmp/r.sh; true"
    )
    salida = dc("run", "--rm", "--no-deps", "-T", "--entrypoint", "sh", "respaldos", "-c", orden)
    assert "ERROR: la copia de seguridad falló" in salida, salida[-400:]
    assert solicitudes.get(f"{BASE}/api/v1/configuracion/publica").status == 200, "El sistema sigue en marcha"
    try:
        estado = api.get("/configuracion/estado-copias").json()
        assert estado["alerta"] and "falló" in estado["mensaje"], estado
        p = como_admin()
        assert "falló" in p.get_by_test_id("aviso-copias").inner_text(), "El administrador lo ve en pantalla"
        u = fab.usuario()
        assert u.api.get("/configuracion/estado-copias").status == 403
        q = abrir(u.alias, u.clave)
        assert q.get_by_test_id("aviso-copias").count() == 0, "Los demás no"

        # Sin ningún error, pero con el servicio detenido más de un día
        sql("update estado_copias set ultimo_error_en = null, ultima_exitosa = now() - interval '27 hours'")
        estado = api.get("/configuracion/estado-copias").json()
        assert estado["alerta"] and "No se ha creado" in estado["mensaje"], estado
        sql("update estado_copias set ultima_exitosa = now() - interval '1 hour'")
        assert not api.get("/configuracion/estado-copias").json()["alerta"], "Con una copia reciente desaparece el aviso"
    finally:
        sql("update estado_copias set ultimo_error_en = null, ultima_exitosa = now()")


# ---------------- Reinicios y caídas ----------------

def _reinicios(servicio):
    return int(subprocess.run(["docker", "inspect", f"{PROYECTO}-{servicio}-1", "--format", "{{.RestartCount}}"], capture_output=True, text=True).stdout.strip())


@caso("OPE-06")
def test_los_servicios_vuelven_solos(solicitudes, api):
    for servicio in ("db", "backend", "web", "https", "respaldos"):
        politica = subprocess.run(["docker", "inspect", f"{PROYECTO}-{servicio}-1", "--format", "{{.HostConfig.RestartPolicy.Name}}"], capture_output=True, text=True).stdout.strip()
        assert politica == "unless-stopped", (servicio, politica)
    for servicio in ("web", "backend"):
        antes = _reinicios(servicio)
        # Caída del proceso principal, no una parada ordenada de Docker
        dc("exec", "-T", servicio, "sh", "-c", "kill -KILL -1 2>/dev/null; kill -TERM 1", comprobar=False)
        _esperar(lambda: _reinicios(servicio) > antes, 40, f"{servicio} no se reinició")
    dc("up", "-d", "--wait", "backend", "web")
    _esperar(lambda: solicitudes.get(f"{BASE}/api/v1/configuracion/publica").status == 200, 60)
    assert api.get("/auth/me").status == 200


@caso("OPE-07")
def test_caida_de_la_base_durante_cobros(fab, api, solicitudes):
    """Sin apagado ordenado, como en un corte: PostgreSQL debe recuperarse sin pagos a medias."""
    fab.caja()
    paciente = fab.paciente()
    marca = f"Corte{uuid4().hex[:8]}"
    aceptados = []
    detener = threading.Event()

    def cobrar():
        while not detener.is_set():
            estado = peticion_directa("POST", "/caja/pagos", api.token, {"paciente_id": paciente["id"], "monto": 1, "metodo_pago": "TRANSFERENCIA", "es_cobro_directo": True, "observaciones": marca})
            if estado == 201:
                aceptados.append(1)

    hilos = [threading.Thread(target=cobrar, daemon=True) for _ in range(4)]
    for hilo in hilos:
        hilo.start()
    try:
        time.sleep(4)
        assert aceptados, "Los cobros estaban entrando"
        caidas = _reinicios("db")
        dc("exec", "-T", "db", "sh", "-c", 'gosu postgres pg_ctl -D "$PGDATA" stop -m immediate', comprobar=False)
        _esperar(lambda: _reinicios("db") > caidas, 30, "La base no llegó a caer: la prueba no comprobaría nada")
    finally:
        detener.set()
        for hilo in hilos:
            hilo.join(70)

    def responde():
        try:
            return api.get("/auth/me").status == 200
        except Exception:  # El proxy puede rechazar la conexión mientras vuelve
            return False

    _esperar(responde, 90, "El sistema no volvió tras la caída de la base")
    assert sql("select count(*) from pg_stat_database where datname = current_database()") == "1"
    registrados = int(sql(f"select count(*) from pagos where observaciones = '{marca}'"))
    assert registrados >= len(aceptados), f"Se perdieron cobros confirmados: {registrados} de {len(aceptados)}"
    # Los pagos son completos: el saldo cuenta exactamente lo registrado
    total = float(sql(f"select coalesce(sum(monto), 0) from pagos where observaciones = '{marca}'"))
    assert total == registrados
    assert fab.cobro_directo(paciente["id"], 1)["id"], "Se sigue cobrando"


# ---------------- Conexión ----------------

@caso("RED-06")
def test_puerto_directo_solo_en_el_servidor():
    puerto = 8081
    ligaduras = subprocess.run(["docker", "inspect", f"{PROYECTO}-web-1", "--format", "{{json .HostConfig.PortBindings}}"], capture_output=True, text=True).stdout
    assert '"HostIp":"127.0.0.1"' in ligaduras
    with socket.create_connection(("127.0.0.1", puerto), timeout=5):
        pass
    direcciones = [d[4][0] for d in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET) if not d[4][0].startswith("127.")]
    for direccion in direcciones:
        with socket.socket() as s:
            s.settimeout(3)
            assert s.connect_ex((direccion, puerto)) != 0, f"Responde por {direccion}"


@caso("SEG-02")
def test_codigo_en_los_campos_se_muestra_como_texto(fab, api, abrir):
    carga = "<img src=x onerror=\"window.__xss=1\"><script>window.__xss=1</script>"
    paciente = fab.paciente(nombres=f"XSS{carga}"[:100], apellidos=carga[:100], direccion=carga, ocupacion=carga)
    pid = paciente["id"]
    assert api.put(f"/pacientes/{pid}/antecedentes", {"alergias": carga, "enfermedades_sistemicas": carga, "medicamentos_actuales": carga}).ok
    tratamiento = fab.tratamiento(1, nombre=f"XSS{carga}"[:200])
    plan = api.post("/tratamientos/planes", {"paciente_id": pid, "doctor_id": fab.doctor, "titulo": carga[:100]}).json()["id"]
    fab.item(plan, tratamiento["id"], 1, pieza_fdi=11, superficie="OCLUSAL")
    hoy = ahora_clinica().strftime("%Y-%m-%d")
    fab.cita(pid, hoy, "17:00", "17:30", motivo=carga, notas=f"Box 1 {carga}")
    sillon = api.post("/sillones/", {"nombre": f"X{carga}"[:100]}).json()
    assert api.post("/visitas/", {"paciente_id": pid, "doctor_id": fab.doctor, "motivo_consulta": carga, "observaciones_clinicas": carga, "diagnostico": carga, "procedimiento_realizado": carga, "receta_medicamentos": carga}).status == 201
    assert api.post("/radiografias/", {"paciente_id": pid, "tipo_estudio": "PERIAPICAL", "titulo": carga[:100], "archivo_url": "https://ejemplo.test/a.jpg", "informe_diagnostico": carga}).status == 201
    assert api.post("/protesis/", {"paciente_id": pid, "doctor_id": fab.doctor, "laboratorio_nombre": carga[:100], "tipo_trabajo": "CORONA_ZIRCONIO", "instrucciones_tecnicas": carga, "observaciones": carga}).ok
    fab.caja()
    fab.cobro_directo(pid, 1, observaciones=carga)
    assert api.post("/caja/egresos", {"categoria": "OTRO", "monto": 1, "concepto_motivo": carga[:200]}).ok
    original = api.get("/configuracion/").json()["nombre_clinica"]
    assert api.put("/configuracion/", {"nombre_clinica": carga[:120]}).ok
    u = fab.usuario(nombre=carga[:100], apellido=carga[:100])
    try:
        p = abrir("admin", CLAVE_ADMIN)
        alertas = []
        p.on("dialog", lambda d: (alertas.append(d.message), d.dismiss()))
        rutas = ["", "pacientes", f"pacientes?paciente_id={pid}", f"odontograma?paciente_id={pid}", "citas", f"evolucion?paciente_id={pid}", f"radiografias?paciente_id={pid}", "protesis", "caja", f"cobranzas?paciente_id={pid}", "nomina", "auditoria", "reportes", "tratamientos", "sillones", "configuracion", "usuarios"]
        for ruta in rutas:
            p.goto(f"{BASE}/{ruta}")
            p.wait_for_load_state("networkidle")
            p.wait_for_timeout(250)
            assert p.evaluate("window.__xss") is None, f"Se ejecutó código en {ruta}"
            assert p.locator('img[src="x"]').count() == 0, f"Se insertó HTML en {ruta}"
        assert not alertas
        # Y el texto se ve tal cual, por ejemplo en la lista de citas
        p.goto(f"{BASE}/tratamientos")
        p.wait_for_load_state("networkidle")
        assert "<script>" in p.inner_text("main") or "<img" in p.inner_text("main")
    finally:
        api.put("/configuracion/", {"nombre_clinica": original})
        api.delete(f"/sillones/{sillon['id']}")
        assert u.id


# ---------------- Flujos completos ----------------

@caso("E2E-10")
def test_protesis_de_principio_a_fin(fab, api):
    fab.caja()
    pid = fab.paciente()["id"]
    plan = fab.plan(pid)
    item = fab.item(plan, fab.tratamiento(900, categoria="REHABILITACION_PROTESIS")["id"], 900, pieza_fdi=16, superficie="OCLUSAL")
    assert api.put(f"/tratamientos/planes/{plan}", {"estado": "APROBADO"}).ok
    assert fab.saldo(pid) == 900, "Presupuesto"
    orden = api.post("/protesis/", {"paciente_id": pid, "doctor_id": fab.doctor, "item_plan_id": item["id"], "laboratorio_nombre": "Lab E2E", "tipo_trabajo": "CORONA_ZIRCONIO", "costo_laboratorio": 250})
    assert orden.ok, orden.text
    orden = orden.json()
    for estado in ("EN_LABORATORIO", "RECIBIDO_EN_CLINICA", "PRUEBA_EN_BOCA", "INSTALADO_FINALIZADO"):
        cambios = {"estado": estado}
        if estado == "RECIBIDO_EN_CLINICA":
            cambios["fecha_recepcion_real"] = ahora_clinica().strftime("%Y-%m-%d")  # Lo envía la pantalla
        assert api.put(f"/protesis/{orden['id']}", cambios).ok, estado
        assert next(o for o in api.get("/protesis/").json() if o["id"] == orden["id"])["estado"] == estado
    final = next(o for o in api.get("/protesis/").json() if o["id"] == orden["id"])
    assert final["fecha_recepcion_real"], "Recepción registrada"
    gaveta = fab.gaveta()
    assert api.post(f"/protesis/{orden['id']}/pagar-laboratorio", {}).ok
    assert fab.gaveta() == gaveta - 250, "Pago al laboratorio"
    etapas = [a for a in fab.auditoria("ordenes_laboratorio_protesis") if a["registro_id"] == orden["id"]]
    assert len(etapas) >= 5, f"Cada etapa queda registrada: {len(etapas)}"


@caso("CCI-18")
def test_auditoria_de_la_cuenta_de_cita(fab, api):
    fab.caja()
    pid = fab.paciente()["id"]
    plan = fab.plan(pid)
    item = fab.item(plan, fab.tratamiento(100)["id"], 100, pieza_fdi=11, superficie="OCLUSAL")
    assert api.put(f"/tratamientos/planes/{plan}", {"estado": "APROBADO"}).ok
    cita = fab.cita(pid, item_plan_id=item["id"]).json()
    assert api.put(f"/citas/{cita['id']}", {"estado": "FINALIZADA"}).ok
    cuenta = next(c for c in api.get("/cobros-cita/").json() if c["cita_id"] == cita["id"])
    lineas = [{"id": l["id"], "concepto": l["concepto"], "monto": 80} for l in cuenta["lineas"]]
    assert api.put(f"/cobros-cita/{cuenta['id']}", {"lineas": lineas}).ok
    assert api.post(f"/cobros-cita/{cuenta['id']}/confirmar", {"metodo_pago": "TRANSFERENCIA", "doctor_comision_id": fab.doctor}).ok
    secciones = {a["seccion_consultada"] for a in fab.auditoria("cobros_cita") if a["registro_id"] == cuenta["id"]}
    assert {"COBRO_CITA_CREADO", "COBRO_CITA_EDITADO", "COBRO_CITA_PAGADO"} <= secciones, secciones


def _copiar_y_restaurar(consulta_extra=""):
    salida = dc("run", "--rm", "respaldo")
    assert "Copia creada y comprobada" in salida, salida[-300:]
    archivo = sorted(RESPALDOS.glob("clinica_docker_*.dump"), key=lambda a: a.stat().st_mtime)[-1]
    base = f"qa_rest_{uuid4().hex[:6]}"
    orden = (
        f"export PGPASSWORD=$POSTGRES_PASSWORD; createdb -U $POSTGRES_USER {base} && "
        f"pg_restore -U $POSTGRES_USER --no-owner --exit-on-error -d {base} /backups/{archivo.name}"
    )
    salida = dc("exec", "-T", "respaldos", "sh", "-c", orden)
    assert "error" not in salida.lower(), salida[-300:]
    return base


def _en_base(base, consulta):
    return dc("exec", "-T", "db", "sh", "-c", f'psql -U "$POSTGRES_USER" -d {base} -Atc "{consulta}"').strip()


HUELLA = (
    "select string_agg(t.table_name || '=' || (xpath('/row/c/text()', query_to_xml('select count(*) c, md5(string_agg(x::text, chr(44) order by x::text)) h from ' || quote_ident(t.table_name) || ' x', false, true, '')))[1]::text, ' ' order by t.table_name) "
    "from information_schema.tables t where t.table_schema = 'public' and t.table_type = 'BASE TABLE'"
)


@caso("E2E-11", "CFG-11", "RAD-15")
def test_jornada_copia_y_restauracion(fab, api, tmp_path):
    original = api.get("/configuracion/").json()
    # Jornada: paciente, plan, cita atendida, cobro, egreso, radiografía y marca propia
    fab.caja()
    pid = fab.paciente(nombres=f"Jornada{uuid4().hex[:6]}")["id"]
    plan = fab.plan(pid)
    item = fab.item(plan, fab.tratamiento(300)["id"], 300, pieza_fdi=36, superficie="OCLUSAL")
    assert api.put(f"/tratamientos/planes/{plan}", {"estado": "APROBADO"}).ok
    cita = fab.cita(pid, item_plan_id=item["id"]).json()
    assert api.put(f"/citas/{cita['id']}", {"estado": "FINALIZADA"}).ok
    cuenta = next(c for c in api.get("/cobros-cita/").json() if c["cita_id"] == cita["id"])
    assert api.post(f"/cobros-cita/{cuenta['id']}/confirmar", {"metodo_pago": "EFECTIVO", "doctor_comision_id": fab.doctor}).ok
    assert api.post("/caja/egresos", {"categoria": "OTRO", "monto": 5, "concepto_motivo": "Jornada"}).ok
    enlace = "https://ejemplo.test/jornada.jpg"
    rx = api.post("/radiografias/", {"paciente_id": pid, "tipo_estudio": "PERIAPICAL", "titulo": "Jornada", "archivo_url": enlace}).json()
    nombre = f"Clínica restaurada {uuid4().hex[:4]}"
    assert api.put("/configuracion/", {"nombre_clinica": nombre, "moneda_simbolo": "Bs."}).ok
    logo = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000" "1f15c4890000000d49444154789c6360606060000000050001a5f645400000000049454e44ae426082")
    sql(f"update configuracion_clinica set logo = decode('{logo.hex()}', 'hex'), logo_tipo = 'image/png'")

    # Sin escrituras en curso: la copia y la original deben coincidir por completo
    huella_original = sql(HUELLA)
    base = _copiar_y_restaurar()
    try:
        huella_restaurada = _en_base(base, HUELLA)
        assert huella_restaurada == huella_original, "Todas las tablas coinciden"
        assert "pagos=" in huella_original and "citas=" in huella_original
        assert _en_base(base, "select nombre_clinica || '/' || moneda_simbolo || '/' || logo_tipo || '/' || encode(logo, 'hex') from configuracion_clinica") == f"{nombre}/Bs./image/png/{logo.hex()}", "Vuelven el logo y la configuración"
        assert _en_base(base, f"select archivo_url from radiografias_estudios where id = '{rx['id']}'") == enlace, "Vuelve el registro; la imagen sigue dependiendo de su enlace"
    finally:
        _en_base("postgres", f"drop database {base}")
        api.put("/configuracion/", {"nombre_clinica": original["nombre_clinica"], "moneda_simbolo": original["moneda_simbolo"]})


# ---------------- Instalar y actualizar en carpetas limpias ----------------

class InstalacionAparte:
    """Otra copia del proyecto, con su propia base y sus puertos. Se elimina al terminar."""

    def __init__(self, nombre, carpeta, puerto, version):
        self.proyecto, self.carpeta, self.puerto = nombre, carpeta, puerto
        self.entorno = {**os.environ, "CLINICA_PUERTO_WEB": str(puerto), "CLINICA_RESPALDOS": str(carpeta / "copias")}
        (carpeta.parent).mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", str(RAIZ), str(carpeta)], check=True, capture_output=True)
        self.git("checkout", "-q", version)
        (carpeta / "copias").mkdir()
        # Las primeras versiones tienen el puerto fijo, y ese puerto lo usa la instalación real
        (carpeta / "docker-compose.override.yml").write_text(f'services:\n  web:\n    ports: !override\n      - "127.0.0.1:{puerto}:8080"\n', encoding="utf-8")

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.carpeta, check=True, capture_output=True)

    def docker(self, *args):
        r = subprocess.run(["docker", "compose", "-p", self.proyecto, *args], cwd=self.carpeta, env=self.entorno, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=560)
        if r.returncode != 0:
            registros = subprocess.run(["docker", "compose", "-p", self.proyecto, "logs", "--tail", "25"], cwd=self.carpeta, env=self.entorno, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
            raise AssertionError(f"{args}: {r.stderr[-300:]}\n{registros[-1800:]}")
        return r.stdout + r.stderr

    def preparar(self):
        r = subprocess.run(["python", "scripts/preparar_docker.py", "--zona", "America/La_Paz"], cwd=self.carpeta, capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert r.returncode == 0, r.stderr[-400:]

    def sql(self, consulta):
        return self.docker("exec", "-T", "db", "sh", "-c", f'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "{consulta}"').strip()

    def web(self, ruta="/"):
        return subprocess.run(["curl", "-s", "-o", "NUL", "-w", "%{http_code}", f"http://localhost:{self.puerto}{ruta}"], capture_output=True, text=True).stdout

    def eliminar(self):
        subprocess.run(["docker", "compose", "-p", self.proyecto, "--profile", "herramientas", "down", "-v"], cwd=self.carpeta, env=self.entorno, capture_output=True)
        shutil.rmtree(self.carpeta, ignore_errors=True, onerror=None)


@pytest.fixture
def instalacion(tmp_path_factory):
    creadas = []

    def _crear(nombre, puerto, version):
        carpeta = Path(tmp_path_factory.mktemp("instalacion")) / "proyecto"
        creadas.append(InstalacionAparte(nombre, carpeta, puerto, version))
        return creadas[-1]

    yield _crear
    for aparte in creadas:
        aparte.eliminar()
    # La imagen queda con el nombre del proyecto: se reconstruye la de la versión actual
    dc("build", "backend", "web")


@caso("OPE-01")
def test_instalar_desde_cero_con_la_guia(instalacion):
    actual = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RAIZ, capture_output=True, text=True).stdout.strip()
    aparte = instalacion("clinica-limpia", 8082, actual)
    aparte.preparar()
    aparte.docker("up", "--build", "-d", "--wait")
    assert aparte.web() == "200"
    admin = _valor_env_de(aparte.carpeta / ".env.docker.admin", "ADMIN_PASSWORD")
    resultado = subprocess.run(["curl", "-s", "-o", "NUL", "-w", "%{http_code}", "-d", f"username=admin&password={urllib.parse.quote(admin)}", f"http://localhost:8082/api/v1/auth/login"], capture_output=True, text=True).stdout
    assert resultado == "200", "Se entra con la contraseña generada"
    assert aparte.sql("select count(*) from sillones where activo") == "3"


def _valor_env_de(archivo, clave):
    for linea in Path(archivo).read_text(encoding="utf-8").splitlines():
        if linea.startswith(f"{clave}="):
            return linea.split("=", 1)[1].strip()
    raise KeyError(clave)


@caso("OPE-13")
def test_actualizar_con_datos(instalacion):
    actual = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RAIZ, capture_output=True, text=True).stdout.strip()
    aparte = instalacion("clinica-actualiza", 8083, VERSION_ANTERIOR)
    aparte.preparar()
    aparte.docker("up", "--build", "-d", "--wait")
    aparte.sql(
        "insert into pacientes (nombres, apellidos, tipo_documento, numero_documento, genero, fecha_nacimiento, telefono) "
        "select 'Antiguo', 'P' || g, 'CI', 'ANT' || g, 'OTRO', '1980-01-01', '700' from generate_series(1, 500) g"
    )
    antes = aparte.sql("select count(*), md5(string_agg(id::text || numero_documento, chr(44) order by id)) from pacientes")
    migraciones_antes = int(aparte.sql("select count(*) from migraciones_aplicadas"))
    # Tal como indica la guía: copia y actualización
    assert "Copia creada y comprobada" in aparte.docker("run", "--rm", "respaldo")
    aparte.git("checkout", "-q", actual)
    aparte.docker("up", "--build", "-d", "--wait")
    assert aparte.sql("select count(*), md5(string_agg(id::text || numero_documento, chr(44) order by id)) from pacientes") == antes, "No se pierde nada"
    assert int(aparte.sql("select count(*) from migraciones_aplicadas")) == len(list((RAIZ / "database" / "migraciones").glob("*.sql"))) >= migraciones_antes
    assert aparte.web() == "200"


# ---------------- Volumen y rendimiento ----------------

@pytest.fixture(scope="module")
def volumen(api):
    """Años de datos: 20.000 pacientes, 40.000 pagos, 5.100 citas el mes próximo y 200 empleados."""
    doctor = sql("select id from doctores limit 1")
    registrador = sql("select id from usuarios where username = 'admin'")
    sql(
        "insert into pacientes (nombres, apellidos, tipo_documento, numero_documento, genero, fecha_nacimiento, telefono) "
        "select 'Volumen', 'P' || g, 'CI', 'VOL' || g, 'OTRO', '1980-01-01', '700' from generate_series(1, 20000) g"
    )
    sql(
        "insert into pagos (paciente_id, registrado_por_usuario_id, monto, metodo_pago, es_cobro_directo, fecha_hora) "
        f"select id, '{registrador}', 10, 'TRANSFERENCIA', true, now() - (random() * 1000 || ' days')::interval "
        "from pacientes cross join generate_series(1, 2) where numero_documento like 'VOL%'"
    )
    primero = (ahora_clinica().replace(day=28) + timedelta(days=4)).replace(day=2, hour=12, minute=0, second=0, microsecond=0)
    sql(
        "insert into citas (paciente_id, doctor_id, fecha_inicio_programada, fecha_fin_programada, motivo_consulta, notas_adicionales, estado) "
        f"select id, '{doctor}', '{primero.isoformat()}'::timestamptz + (row_number() over () % 20 || ' days')::interval, '{primero.isoformat()}'::timestamptz + (row_number() over () % 20 || ' days')::interval + interval '1 minute', 'Volumen', 'Box 1', 'PROGRAMADA' "
        "from (select id from pacientes where numero_documento like 'VOL%' limit 5100) p"
    )
    rol = sql("select id from roles where codigo = 'RECEPCION'")
    clave = sql("select password_hash from usuarios where username = 'admin'")
    sql(
        "insert into usuarios (username, password_hash, nombre, apellido, email, rol_id, activo) "
        f"select 'vol' || g, '{clave}', 'Empleado', 'V' || g, 'vol' || g || '@clinica-pruebas.com', '{rol}', true from generate_series(1, 200) g"
    )
    sql("analyze")
    return primero


def _tiempo(funcion):
    inicio = time.perf_counter()
    resultado = funcion()
    return time.perf_counter() - inicio, resultado


@caso("REN-02")
def test_busqueda_de_pacientes_rapida(api, volumen):
    for termino in ("VOL19999", "Volumen P1500", "700"):
        segundos, respuesta = _tiempo(lambda t=termino: api.get("/pacientes/", q=t))
        assert respuesta.ok and respuesta.json(), termino
        assert segundos < 1, (termino, segundos)


@caso("REN-03")
def test_reportes_con_todo_el_historial(api, volumen):
    for ruta in ("/reportes/resumen-financiero", "/reportes/productividad-doctores", "/reportes/tratamientos-demanda"):
        segundos, respuesta = _tiempo(lambda r=ruta: api.get(r))
        assert respuesta.ok and segundos < 5, (ruta, segundos)


@caso("REN-04")
def test_agenda_de_un_mes_con_mas_de_5000_citas(como_admin, volumen):
    p = como_admin("citas")
    p.get_by_role("button", name="Vista Mensual").click()
    p.wait_for_load_state("networkidle")
    inicio = time.perf_counter()
    p.get_by_title("Mes Siguiente").click()
    p.get_by_text("Se muestran las primeras 5000 citas del período").wait_for(timeout=20000)
    p.wait_for_load_state("networkidle")
    assert time.perf_counter() - inicio < 20
    assert "más..." in p.inner_text("main")


@caso("REN-05")
def test_tiempo_y_tamano_de_la_copia(volumen):
    segundos, salida = _tiempo(lambda: dc("run", "--rm", "respaldo"))
    assert "Copia creada y comprobada" in salida
    archivo = sorted(RESPALDOS.glob("clinica_docker_*.dump"), key=lambda a: a.stat().st_mtime)[-1]
    mb = archivo.stat().st_size / 1024 / 1024
    print(f"Copia con volumen: {segundos:.0f} s, {mb:.1f} MB")
    assert segundos < 120 and mb < 200, (segundos, mb)


@caso("REN-07")
def test_nomina_y_productividad_con_muchos_usuarios(api, volumen):
    for ruta in ("/empleados/personal", "/reportes/productividad-doctores", "/usuarios/"):
        segundos, respuesta = _tiempo(lambda r=ruta: api.get(r))
        assert respuesta.ok and segundos < 3, (ruta, segundos)


def _memoria_mb(servicio="backend"):
    texto = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", f"{PROYECTO}-{servicio}-1"], capture_output=True, text=True).stdout
    valor, unidad = re.match(r"([\d.]+)(\w+)", texto).groups()
    return float(valor) * {"KiB": 1 / 1024, "MiB": 1, "GiB": 1024}[unidad]


@caso("RED-10", "REN-06")
def test_cinco_equipos_a_la_vez(fab, api, volumen):
    """Cinco clientes durante 3 minutos, con la mezcla de una jornada, sobre una base con años de datos."""
    fab.caja()
    pid = fab.paciente()["id"]
    errores, tiempos = [], []
    fin = time.time() + 180
    rutas = ["/pacientes/?q=Volumen", "/citas/?limit=100", "/caja/estado", "/reportes/resumen-financiero?fecha_desde=2026-01-01T00:00:00Z", "/auditoria/?limit=100", "/tratamientos/catalogo"]
    memoria_inicial = _memoria_mb()
    muestras = []

    def trabajar(equipo):
        indice = equipo
        while time.time() < fin:
            ruta = rutas[indice % len(rutas)]
            inicio = time.perf_counter()
            estado = peticion_directa("GET", ruta, api.token)
            tiempos.append(time.perf_counter() - inicio)
            if estado >= 400:
                errores.append((ruta, estado))
            if indice % 7 == 0:
                estado = peticion_directa("POST", "/caja/pagos", api.token, {"paciente_id": pid, "monto": 1, "metodo_pago": "TRANSFERENCIA", "es_cobro_directo": True, "observaciones": "Carga"})
                if estado != 201:
                    errores.append(("cobro", estado))
            indice += 1
            time.sleep(0.5)

    hilos = [threading.Thread(target=trabajar, args=(i,), daemon=True) for i in range(5)]
    for hilo in hilos:
        hilo.start()
    while time.time() < fin:
        muestras.append(_memoria_mb())
        time.sleep(30)
    for hilo in hilos:
        hilo.join(120)
    tiempos.sort()
    percentil = tiempos[int(len(tiempos) * 0.95)]
    print(f"{len(tiempos)} peticiones, p95 {percentil:.2f} s, memoria {memoria_inicial:.0f} → {muestras[-1]:.0f} MiB")
    assert not errores, errores[:5]
    assert percentil < 2, percentil
    # Estabilizada tras el primer minuto, no sigue creciendo
    assert muestras[-1] < muestras[2] * 1.25 + 30, muestras


# ---------------- Espera real: debe ir al final, porque un reinicio borra el bloqueo ----------------

@caso("ACC-07")
def test_bloqueo_termina_a_los_quince_minutos(fab, sin_sesion):
    u = fab.usuario()
    bloquear(sin_sesion, u.alias)
    time.sleep(15 * 60 + 5)
    assert sin_sesion.login(u.alias, u.clave).status == 200


_ = (ssl, CLAVE_ADMIN, ENTORNO)
