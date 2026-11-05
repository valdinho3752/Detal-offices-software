"""Utilidades de las pruebas: conexión a la instalación de QA, datos de prueba y accesos."""
import json
import os
import random
import ssl
import subprocess
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parents[2]
PROYECTO = "clinica-qa"
BASE = os.getenv("QA_BASE", "https://localhost:8443")
API = f"{BASE}/api/v1"
RESPALDOS = RAIZ / "qa" / "resultados" / "respaldos"
ENTORNO = {
    **os.environ,
    "CLINICA_PUERTO_WEB": "8081",
    "CLINICA_PUERTO_HTTP": "8180",
    "CLINICA_PUERTO_HTTPS": "8443",
    "CLINICA_RESPALDOS": str(RESPALDOS),
    "RESPALDO_HORA": "0",
}
CLAVE = "Prueba1234!"
CLAVE_INICIAL = "Inicial1234!"
ANCHOS = (1280, 1366, 1536, 1920, 2560)


def _valor_env(archivo, clave):
    for linea in (RAIZ / archivo).read_text(encoding="utf-8").splitlines():
        if linea.startswith(f"{clave}="):
            return linea.split("=", 1)[1].strip()
    raise KeyError(clave)


CLAVE_ADMIN = _valor_env(".env.docker.admin", "ADMIN_PASSWORD")
ZONA = _valor_env(".env.docker", "CLINICA_TIMEZONE")


def ahora_clinica():
    return datetime.now(ZoneInfo(ZONA))


def dc(*args, comprobar=True):
    resultado = subprocess.run(
        ["docker", "compose", "-p", PROYECTO, "--profile", "https", *args],
        cwd=RAIZ, env=ENTORNO, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if comprobar and resultado.returncode != 0:
        raise RuntimeError(f"{args}: {resultado.stderr[-800:]}")
    return resultado.stdout + resultado.stderr


def sql(consulta):
    """Ejecuta SQL solo en la base del proyecto de QA."""
    return dc("exec", "-T", "db", "sh", "-c", f'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "{consulta}"').strip()


# Inicio al azar: al reutilizar la instalación no choca con las citas de otra ejecución
_ultimo_dia = [date(2040, 1, 1) + timedelta(days=random.randrange(15000))]


def dia_libre():
    """Un día distinto en cada llamada: las pruebas de agenda no chocan entre sí."""
    _ultimo_dia[0] += timedelta(days=1)
    return _ultimo_dia[0].isoformat()


def peticion_directa(metodo, ruta, token, cuerpo=None, cabeceras=None):
    """Sin Playwright: se puede usar desde varios hilos en las pruebas de simultaneidad."""
    contexto = ssl.create_default_context()
    contexto.check_hostname = False
    contexto.verify_mode = ssl.CERT_NONE
    encabezados = {"Content-Type": "application/json", **(cabeceras or {})}
    if token:
        encabezados["Authorization"] = f"Bearer {token}"
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    solicitud = urllib.request.Request(API + ruta, data=datos, method=metodo, headers=encabezados)
    try:
        with urllib.request.urlopen(solicitud, context=contexto, timeout=60) as respuesta:
            return respuesta.status
    except urllib.error.HTTPError as error:
        return error.code


class Respuesta:
    def __init__(self, crudo):
        self.status = crudo.status
        self.text = crudo.text()
        self.headers = crudo.headers

    def json(self):
        return json.loads(self.text)

    @property
    def detalle(self):
        try:
            return str(self.json().get("detail", ""))
        except (ValueError, AttributeError):
            return ""

    @property
    def ok(self):
        return 200 <= self.status < 300


class Api:
    def __init__(self, solicitudes, token=None):
        self._solicitudes = solicitudes
        self.token = token

    def _cabeceras(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def get(self, ruta, **params):
        return Respuesta(self._solicitudes.get(API + ruta, headers=self._cabeceras(), params=params or None))

    def post(self, ruta, cuerpo=None):
        return Respuesta(self._solicitudes.post(API + ruta, headers=self._cabeceras(), data=cuerpo if cuerpo is not None else {}))

    def put(self, ruta, cuerpo=None):
        return Respuesta(self._solicitudes.put(API + ruta, headers=self._cabeceras(), data=cuerpo if cuerpo is not None else {}))

    def patch(self, ruta, cuerpo=None):
        return Respuesta(self._solicitudes.patch(API + ruta, headers=self._cabeceras(), data=cuerpo if cuerpo is not None else {}))

    def delete(self, ruta):
        return Respuesta(self._solicitudes.delete(API + ruta, headers=self._cabeceras()))

    def login(self, usuario, clave):
        return Respuesta(self._solicitudes.post(f"{API}/auth/login", form={"username": usuario, "password": clave}))

    def como(self, token):
        return Api(self._solicitudes, token)


class Usuario:
    def __init__(self, alias, datos, api, clave):
        self.alias, self.id, self.api, self.clave = alias, datos["id"], api, clave
        self.doctor_id = api.get("/auth/me").json().get("doctor_id") if api.token else None


class Fabrica:
    """Crea los datos que necesita cada prueba, siempre por la API."""

    def __init__(self, admin):
        self.admin = admin
        self.roles = {r["codigo"]: r["id"] for r in admin.get("/usuarios/roles").json()}
        self.doctor = admin.get("/usuarios/doctores/lista").json()[0]["id"]

    def usuario(self, rol="ASISTENTE", cambiar_clave=True, nombre="QA", apellido="Prueba", **contrato):
        alias = f"qa_{uuid4().hex[:10]}"
        res = self.admin.post("/usuarios/", {
            "username": alias, "password": CLAVE_INICIAL, "nombre": nombre, "apellido": apellido,
            "email": f"{alias}@clinica-pruebas.com", "rol_id": self.roles.get(rol, rol),
        })
        assert res.status == 201, res.text
        datos = res.json()
        token = self.admin.login(alias, CLAVE_INICIAL).json()["access_token"]
        api = self.admin.como(token)
        clave = CLAVE_INICIAL
        if cambiar_clave:
            token = api.post("/auth/cambiar-contrasena", {"actual": CLAVE_INICIAL, "nueva": CLAVE}).json()["access_token"]
            api = self.admin.como(token)
            clave = CLAVE
        if contrato:
            assert self.admin.post("/personal/contratos", {"usuario_id": datos["id"], **contrato}).status == 201
        return Usuario(alias, datos, api, clave)

    def paciente(self, **extra):
        res = self.admin.post("/pacientes/", {
            "nombres": "Paciente", "apellidos": "QA", "tipo_documento": "CI", "numero_documento": f"QA-{uuid4().hex[:10]}",
            "genero": "OTRO", "fecha_nacimiento": "1990-01-01", "telefono": "70000000", **extra,
        })
        assert res.status == 201, res.text
        return res.json()

    def tratamiento(self, costo=100, nombre=None, categoria="PREVENCION"):
        codigo = f"QA{uuid4().hex[:8]}"
        res = self.admin.post("/tratamientos/catalogo", {"codigo": codigo, "categoria": categoria, "nombre": nombre or f"Tratamiento {codigo}", "costo_base": costo})
        assert res.status == 201, res.text
        return res.json()

    def plan(self, paciente_id, costo=None, doctor=None):
        res = self.admin.post("/tratamientos/planes", {"paciente_id": paciente_id, "doctor_id": doctor or self.doctor, "titulo": "Plan QA"})
        assert res.status == 201, res.text
        plan_id = res.json()["id"]
        if costo:
            assert self.admin.put(f"/tratamientos/planes/{plan_id}", {"estado": "APROBADO", "costo_total": costo}).ok
        return plan_id

    def item(self, plan_id, tratamiento_id, costo=100, **extra):
        res = self.admin.post("/tratamientos/items", {"plan_id": plan_id, "tratamiento_id": tratamiento_id, "costo_acordado": costo, **extra})
        assert res.status == 201, res.text
        return res.json()

    def cita(self, paciente_id, dia=None, inicio="09:00", fin="10:00", box=1, doctor=None, **extra):
        dia = dia or dia_libre()
        return self.admin.post("/citas/", {
            "paciente_id": paciente_id, "doctor_id": doctor or self.doctor, "motivo_consulta": extra.pop("motivo", "Control QA"),
            "fecha_inicio_programada": f"{dia}T{inicio}:00Z", "fecha_fin_programada": f"{dia}T{fin}:00Z",
            "notas_adicionales": extra.pop("notas", f"Box {box}"), **extra,
        })

    def caja(self, fondo=100000):
        """Deja una caja abierta con al menos ese efectivo."""
        estado = self.admin.get("/caja/estado").json()
        if estado["caja_abierta"] and estado.get("es_del_dia") and estado["saldo_en_gaveta"] >= fondo / 2:
            return estado
        if estado["caja_abierta"]:
            assert self.admin.post("/caja/cerrar", {"total_efectivo_contado": estado["saldo_en_gaveta"]}).ok
        assert self.admin.post("/caja/abrir", {"monto_inicial_fondo": fondo}).status == 201
        return self.admin.get("/caja/estado").json()

    def cerrar_caja(self):
        estado = self.admin.get("/caja/estado").json()
        if estado["caja_abierta"]:
            assert self.admin.post("/caja/cerrar", {"total_efectivo_contado": estado["saldo_en_gaveta"]}).ok

    def cobro_directo(self, paciente_id, monto=100, metodo="TRANSFERENCIA", **extra):
        res = self.admin.post("/caja/pagos", {"paciente_id": paciente_id, "monto": monto, "metodo_pago": metodo, "es_cobro_directo": True, "observaciones": "Consulta", **extra})
        assert res.status == 201, res.text
        return res.json()

    def saldo(self, paciente_id):
        return self.admin.get(f"/pacientes/{paciente_id}/saldo").json()["saldo_pendiente"]

    def gaveta(self):
        return self.admin.get("/caja/estado").json()["saldo_en_gaveta"]

    def auditoria(self, tabla):
        return self.admin.get("/auditoria/", tabla_afectada=tabla).json()


def campo(formulario, etiqueta):
    """Control que acompaña a una etiqueta, aunque no esté asociada con htmlFor."""
    return formulario.locator(f'div:has(> label:has-text("{etiqueta}"))').first.locator("input, select, textarea").first


def desborde_de_main(pagina):
    return pagina.evaluate("document.querySelector('main').scrollWidth - document.querySelector('main').clientWidth")
