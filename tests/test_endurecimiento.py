"""
Protecciones de datos y seguridad. Escribe datos y cierra la caja abierta: ejecutar contra una base de pruebas.
"""
import concurrent.futures as cf
import os
import random
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

RAIZ = Path(__file__).resolve().parent.parent
sys.path.append(str(RAIZ))

from fastapi.testclient import TestClient
from app.core.limite_login import MAXIMO_POR_EQUIPO, MAXIMO_POR_USUARIO, VENTANA_SEGUNDOS, LimiteIntentos
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
API = "/api/v1"
CLAVE = "Clave1234!"


def _ok(res, codigo=200):
    assert res.status_code == codigo, f"{res.status_code}: {res.text}"
    return res.json()


def _login(usuario, clave=CLAVE):
    return client.post(f"{API}/auth/login", data={"username": usuario, "password": clave})


def _cabeceras(usuario, clave=CLAVE):
    return {"Authorization": f"Bearer {_ok(_login(usuario, clave))['access_token']}"}


H = _cabeceras("admin", "admin123")
ROLES = {r["codigo"]: r["id"] for r in _ok(client.get(f"{API}/usuarios/roles", headers=H))}
DOCTOR = _ok(client.get(f"{API}/usuarios/doctores/lista", headers=H))[0]["id"]


def _crear_usuario(rol="ASISTENTE", clave=CLAVE):
    nombre = f"end_{uuid4().hex[:10]}"
    res = client.post(f"{API}/usuarios/", json={
        "username": nombre, "password": clave, "nombre": "End", "apellido": "Prueba",
        "email": f"{nombre}@clinica-pruebas.com", "rol_id": ROLES[rol],
    }, headers=H)
    return nombre, res


def _usuario(rol="ASISTENTE"):
    nombre, res = _crear_usuario(rol)
    return nombre, _ok(res, 201)["id"]


def _paciente(**extra):
    return client.post(f"{API}/pacientes/", json={
        "nombres": "End", "apellidos": "Prueba", "tipo_documento": "CI", "numero_documento": f"END-{uuid4().hex[:10]}",
        "genero": "OTRO", "fecha_nacimiento": "1990-01-01", "telefono": "70000000", **extra,
    }, headers=H)


def _estado_caja():
    return _ok(client.get(f"{API}/caja/estado", headers=H))


def _cerrar_caja():
    estado = _estado_caja()
    if estado["caja_abierta"]:
        _ok(client.post(f"{API}/caja/cerrar", json={"total_efectivo_contado": estado["saldo_en_gaveta"]}, headers=H))


def _abrir_caja(fondo=10000):
    if not _estado_caja()["caja_abierta"]:
        _ok(client.post(f"{API}/caja/abrir", json={"monto_inicial_fondo": fondo}, headers=H), 201)


def _a_la_vez(funcion, n=10):
    with cf.ThreadPoolExecutor(n) as hilos:
        return list(hilos.map(lambda _: funcion(), range(n)))


def test_una_sola_caja_abierta():
    _cerrar_caja()
    resultados = _a_la_vez(lambda: client.post(f"{API}/caja/abrir", json={"monto_inicial_fondo": 100}, headers=H).status_code)
    assert resultados.count(201) == 1 and set(resultados) <= {201, 400}, resultados
    _cerrar_caja()
    assert not _estado_caja()["caja_abierta"], "Una sola caja: al cerrarla no queda otra abierta"
    print("✔ Caja: aperturas simultáneas dejan una sola caja abierta.")


def test_citas_simultaneas():
    pid = _ok(_paciente(), 201)["id"]
    dia = date(2060, 1, 1) + timedelta(days=random.randint(0, 3000))
    cuerpo = {
        "paciente_id": pid, "doctor_id": DOCTOR, "motivo_consulta": "Carrera",
        "fecha_inicio_programada": f"{dia}T09:00:00Z", "fecha_fin_programada": f"{dia}T10:00:00Z", "notas_adicionales": "Box 2",
    }
    resultados = _a_la_vez(lambda: client.post(f"{API}/citas/", json=cuerpo, headers=H).status_code)
    assert resultados.count(201) == 1 and set(resultados) <= {201, 409}, resultados
    assert len(_ok(client.get(f"{API}/citas/?paciente_id={pid}", headers=H))) == 1
    print("✔ Agenda: citas simultáneas en el mismo horario crean una sola, y las demás reciben un aviso claro.")


def test_referencias_inexistentes():
    _abrir_caja()
    pid = _ok(_paciente(), 201)["id"]
    base = {"motivo_consulta": "x", "fecha_inicio_programada": "2061-01-01T09:00:00Z", "fecha_fin_programada": "2061-01-01T10:00:00Z", "notas_adicionales": "Box 1"}
    assert client.post(f"{API}/citas/", json={**base, "paciente_id": pid, "doctor_id": str(uuid4())}, headers=H).status_code == 404, "No se reasigna a otro doctor"
    assert client.post(f"{API}/citas/", json={**base, "paciente_id": str(uuid4()), "doctor_id": DOCTOR}, headers=H).status_code == 404
    pago = {"paciente_id": pid, "monto": 5, "metodo_pago": "TRANSFERENCIA", "es_cobro_directo": True, "observaciones": "x"}
    assert client.post(f"{API}/caja/pagos", json={**pago, "doctor_comision_id": str(uuid4())}, headers=H).status_code == 404
    print("✔ Referencias: un paciente o doctor inexistente responde 404.")


def test_datos_extremos_sin_error_interno():
    pid = _ok(_paciente(), 201)["id"]
    _abrir_caja()
    pago = {"paciente_id": pid, "metodo_pago": "TRANSFERENCIA", "es_cobro_directo": True, "observaciones": "x"}
    casos = {
        "nombre larguísimo": lambda: _paciente(nombres="x" * 5000),
        "documento larguísimo": lambda: client.post(f"{API}/pacientes/", json={"nombres": "A", "apellidos": "B", "tipo_documento": "CI", "numero_documento": "9" * 5000, "genero": "OTRO", "fecha_nacimiento": "1990-01-01", "telefono": "7"}, headers=H),
        "carácter nulo": lambda: _paciente(nombres="a\x00b"),
        "motivo larguísimo": lambda: client.post(f"{API}/citas/", json={"paciente_id": pid, "doctor_id": DOCTOR, "motivo_consulta": "x" * 5000, "fecha_inicio_programada": "2062-01-01T09:00:00Z", "fecha_fin_programada": "2062-01-01T10:00:00Z", "notas_adicionales": "Box 1"}, headers=H),
        "pago gigante": lambda: client.post(f"{API}/caja/pagos", json={**pago, "monto": 1e15}, headers=H),
        "pago con 3 decimales": lambda: client.post(f"{API}/caja/pagos", json={**pago, "monto": 10.555}, headers=H),
        "egreso con 3 decimales": lambda: client.post(f"{API}/caja/egresos", json={"categoria": "OTRO", "monto": 1.001, "concepto_motivo": "x"}, headers=H),
        "precio gigante": lambda: client.post(f"{API}/tratamientos/catalogo", json={"codigo": f"E{uuid4().hex[:6]}", "categoria": "PREVENCION", "nombre": "x", "costo_base": 1e14}, headers=H),
        "sueldo gigante": lambda: client.post(f"{API}/personal/contratos", json={"usuario_id": _usuario()[1], "salario_base": 1e14}, headers=H),
        "nacimiento futuro": lambda: _paciente(fecha_nacimiento=(date.today() + timedelta(days=2)).isoformat()),
    }
    for nombre, caso in casos.items():
        res = caso()
        assert 400 <= res.status_code < 500, f"{nombre}: {res.status_code} {res.text[:200]}"
        assert "Traceback" not in res.text and "psycopg2" not in res.text and "SQL" not in res.text, f"{nombre} revela detalles internos: {res.text[:200]}"

    res = client.post(f"{API}/caja/pagos", json={**pago, "monto": 10.55}, headers=H)
    assert res.status_code == 201, res.text
    print("✔ Datos extremos: se rechazan con un mensaje claro y sin revelar detalles internos.")


def test_politica_de_contrasenas():
    for debil in ("1", "abc", "123456", "abcdefgh", "12345678", "admin123", "Password123"):
        _, res = _crear_usuario(clave=debil)
        assert res.status_code == 422, f"{debil}: {res.status_code}"
    nombre, uid = _usuario()
    assert client.put(f"{API}/usuarios/{uid}", json={"password": "abc"}, headers=H).status_code == 422
    _cabeceras(nombre)
    print("✔ Contraseñas: se rechazan las débiles al crear y al cambiar.")


def test_limite_de_intentos():
    nombre, _ = _usuario()
    for _ in range(MAXIMO_POR_USUARIO):
        assert _login(nombre, "incorrecta1").status_code == 401
    res = _login(nombre, CLAVE)
    assert res.status_code == 429 and "Retry-After" in res.headers, "Ni la correcta entra durante el bloqueo"
    assert "intentos" in res.json()["detail"]

    # Un acierto antes del límite reinicia el conteo
    otro, _ = _usuario()
    for _ in range(MAXIMO_POR_USUARIO - 1):
        _login(otro, "incorrecta1")
    _cabeceras(otro)
    for _ in range(MAXIMO_POR_USUARIO - 1):
        assert _login(otro, "incorrecta1").status_code == 401
    assert _login(otro).status_code == 200

    # Un usuario que no existe se trata igual: no revela qué usuarios existen
    fantasma = f"nadie_{uuid4().hex[:8]}"
    for _ in range(MAXIMO_POR_USUARIO):
        assert _login(fantasma, "x").status_code == 401
    assert _login(fantasma, "x").status_code == 429

    # Reloj simulado: el bloqueo vence, y por equipo también hay un tope
    ahora = [1000.0]
    limite = LimiteIntentos(reloj=lambda: ahora[0])
    for _ in range(MAXIMO_POR_USUARIO):
        limite.registrar_fallo("Ana", "1.1.1.1")
    bloqueado = False
    try:
        limite.exigir_permitido("ana", "1.1.1.1")
    except Exception:
        bloqueado = True
    assert bloqueado, "No distingue mayúsculas"
    limite.exigir_permitido("ana", "2.2.2.2")
    ahora[0] += VENTANA_SEGUNDOS + 1
    limite.exigir_permitido("ana", "1.1.1.1")
    for i in range(MAXIMO_POR_EQUIPO):
        limite.registrar_fallo(f"u{i}", "3.3.3.3")
    try:
        limite.exigir_permitido("otra", "3.3.3.3")
        raise AssertionError("Debe frenar a un equipo que prueba muchos usuarios")
    except Exception as error:
        assert getattr(error, "status_code", None) == 429
    print("✔ Login: se bloquea tras varios fallos, por usuario y por equipo, y el bloqueo vence.")


def test_cambio_de_contrasena_propia():
    nombre, uid = _usuario("RECEPCION")
    c = _cabeceras(nombre)
    assert _ok(client.get(f"{API}/auth/me", headers=c))["debe_cambiar_contrasena"] is True, "La contraseña inicial la conoce el administrador"
    url = f"{API}/auth/cambiar-contrasena"
    assert client.post(url, json={"actual": CLAVE, "nueva": "Nueva1234!"}).status_code == 401
    assert client.post(url, json={"actual": "mala", "nueva": "Nueva1234!"}, headers=c).status_code == 400
    assert client.post(url, json={"actual": CLAVE, "nueva": "abc"}, headers=c).status_code == 422
    assert client.post(url, json={"actual": CLAVE, "nueva": CLAVE}, headers=c).status_code == 400

    token = _ok(client.post(url, json={"actual": CLAVE, "nueva": "Nueva1234!"}, headers=c))["access_token"]
    nueva = {"Authorization": f"Bearer {token}"}
    assert _ok(client.get(f"{API}/auth/me", headers=nueva))["debe_cambiar_contrasena"] is False
    assert client.get(f"{API}/auth/me", headers=c).status_code == 401, "Las demás sesiones se cierran"
    assert _login(nombre, CLAVE).status_code == 401 and _login(nombre, "Nueva1234!").status_code == 200

    registros = _ok(client.get(f"{API}/auditoria/?tabla_afectada=usuarios", headers=H))
    assert any(r["registro_id"] == uid and r["seccion_consultada"] == "CAMBIO_CONTRASENA" for r in registros)
    assert "Nueva1234" not in str(registros), "La contraseña no se registra"
    print("✔ Contraseña propia: exige la actual, cierra otras sesiones y queda auditada.")


def test_cambio_por_administrador_cierra_sesiones():
    nombre, uid = _usuario()
    c = _cabeceras(nombre)
    _ok(client.post(f"{API}/auth/cambiar-contrasena", json={"actual": CLAVE, "nueva": "Nueva1234!"}, headers=c))
    c = _cabeceras(nombre, "Nueva1234!")

    _ok(client.put(f"{API}/usuarios/{uid}", json={"telefono": "70000001"}, headers=H))
    assert client.get(f"{API}/auth/me", headers=c).status_code == 200, "Editar otros datos no cierra la sesión"

    _ok(client.put(f"{API}/usuarios/{uid}", json={"password": "Reinicio99!"}, headers=H))
    assert client.get(f"{API}/auth/me", headers=c).status_code == 401, "La sesión anterior ya no sirve"
    assert _ok(client.get(f"{API}/auth/me", headers=_cabeceras(nombre, "Reinicio99!")))["debe_cambiar_contrasena"] is True
    print("✔ Sesiones: restablecer una contraseña invalida las sesiones anteriores y pide cambiarla.")


def test_administrador_no_se_bloquea():
    yo = _ok(client.get(f"{API}/auth/me", headers=H))["id"]
    res = client.put(f"{API}/usuarios/{yo}", json={"activo": False}, headers=H)
    assert res.status_code == 400 and "propia cuenta" in res.json()["detail"]
    res = client.put(f"{API}/usuarios/{yo}", json={"rol_id": ROLES["DOCTOR"]}, headers=H)
    assert res.status_code == 400, "Sería el mismo bloqueo"
    assert _ok(client.get(f"{API}/auth/me", headers=H))["rol"] == "ADMIN"

    # Con otro administrador activo, uno sí puede retirar al otro
    nombre, uid = _usuario("ADMIN")
    otro = _cabeceras(nombre)
    _ok(client.put(f"{API}/usuarios/{uid}", json={"activo": False}, headers=H))
    assert client.get(f"{API}/auth/me", headers=otro).status_code == 403
    print("✔ Administrador: no puede desactivarse ni quitarse el rol a sí mismo.")


def test_recuperar_acceso_por_terminal():
    nombre, uid = _usuario("ADMIN")
    sesion = _cabeceras(nombre)
    _ok(client.put(f"{API}/usuarios/{uid}", json={"activo": False}, headers=H))
    entorno = {**os.environ, "ADMIN_PASSWORD": "Recuperada99!", "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    res = subprocess.run([sys.executable, str(RAIZ / "scripts/restablecer_admin.py"), nombre], cwd=RAIZ, env=entorno, capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert res.returncode == 0, res.stderr[-400:]
    assert client.get(f"{API}/auth/me", headers=sesion).status_code == 401, "Cierra las sesiones anteriores"
    _cabeceras(nombre, "Recuperada99!")

    res = subprocess.run([sys.executable, str(RAIZ / "scripts/restablecer_admin.py"), "no_existe_x"], cwd=RAIZ, env=entorno, capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert res.returncode != 0
    res = subprocess.run([sys.executable, str(RAIZ / "scripts/restablecer_admin.py"), nombre], cwd=RAIZ, env={**entorno, "ADMIN_PASSWORD": "abc"}, capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert res.returncode != 0
    print("✔ Recuperación: un script devuelve el acceso de un administrador bloqueado.")


def test_listados_con_limite():
    pid = _ok(_paciente(), 201)["id"]
    for ruta in ("citas/", "visitas/", "tratamientos/planes", "personal/asistencia"):
        assert client.get(f"{API}/{ruta}?limit=1", headers=H).status_code == 200, ruta
        assert client.get(f"{API}/{ruta}?limit=0", headers=H).status_code == 422, ruta
        assert client.get(f"{API}/{ruta}?limit=999999", headers=H).status_code == 422, ruta
    print("✔ Listados: aceptan un límite y rechazan pedir demasiados registros.")


def _marcar(c, tipo):
    return _ok(client.post(f"{API}/auth/fichar", json={"tipo_evento": tipo}, headers=c))


def test_descanso_completo_en_turno_cerrado():
    nombre, uid = _usuario()
    c = _cabeceras(nombre)
    entrada = _marcar(c, "ENTRADA")
    inicio = datetime.fromisoformat(entrada["fecha_hora"]) - timedelta(seconds=30)
    url = f"{API}/personal/asistencia/correcciones"

    # Se arma un turno cerrado en el pasado reciente, con margen para el descanso
    _marcar(c, "SALIDA")
    registros = _ok(client.get(f"{API}/personal/asistencia", params={"usuario_id": uid}, headers=H))
    salida = next(r for r in registros if r["tipo_evento"] == "SALIDA")
    a = datetime.fromisoformat(entrada["fecha_hora"])
    b = datetime.fromisoformat(salida["fecha_hora"])
    medio1, medio2 = a + (b - a) / 3, a + 2 * (b - a) / 3
    motivo = "Olvidó marcar el descanso"

    assert client.post(url, json={"usuario_id": uid, "tipo_evento": "INICIO_DESCANSO", "fecha_hora": medio1.isoformat(), "motivo": motivo}, headers=H).status_code == 409, "Sin su fin sigue siendo imposible"
    assert client.post(url, json={"usuario_id": uid, "tipo_evento": "SALIDA", "fecha_hora": medio1.isoformat(), "fecha_hora_fin": medio2.isoformat(), "motivo": motivo}, headers=H).status_code == 422, "Solo un descanso tiene fin"
    assert client.post(url, json={"usuario_id": uid, "tipo_evento": "INICIO_DESCANSO", "fecha_hora": medio2.isoformat(), "fecha_hora_fin": medio1.isoformat(), "motivo": motivo}, headers=H).status_code == 422, "El fin va después del inicio"
    fin_tardio = b + timedelta(milliseconds=1)
    assert client.post(url, json={"usuario_id": uid, "tipo_evento": "INICIO_DESCANSO", "fecha_hora": medio1.isoformat(), "fecha_hora_fin": fin_tardio.isoformat(), "motivo": motivo}, headers=H).status_code in (400, 409), "No puede abarcar la salida"

    _ok(client.post(url, json={"usuario_id": uid, "tipo_evento": "INICIO_DESCANSO", "fecha_hora": medio1.isoformat(), "fecha_hora_fin": medio2.isoformat(), "motivo": motivo}, headers=H), 201)
    registros = _ok(client.get(f"{API}/personal/asistencia", params={"usuario_id": uid}, headers=H))
    assert [r["tipo_evento"] for r in registros] == ["SALIDA", "FIN_DESCANSO", "INICIO_DESCANSO", "ENTRADA"]
    assert sum(r["es_correccion"] for r in registros) == 2
    print("✔ Corrección: se puede agregar un descanso completo dentro de un turno cerrado.")


def test_anular_marcaje_por_error():
    nombre, uid = _usuario()
    c = _cabeceras(nombre)
    _marcar(c, "ENTRADA")
    salida = _marcar(c, "SALIDA")
    url = f"{API}/personal/asistencia"
    estado = lambda: _ok(client.get(f"{API}/auth/fichaje/estado", headers=c))

    assert estado()["estado"] == "TURNO_CERRADO"
    assert client.post(f"{url}/{salida['id']}/anular", json={"motivo": "  "}, headers=H).status_code == 422
    assert client.post(f"{url}/{salida['id']}/anular", json={"motivo": "Marcó por error"}, headers=c).status_code == 403
    assert client.post(f"{url}/{uuid4()}/anular", json={"motivo": "x"}, headers=H).status_code == 404

    anulado = _ok(client.post(f"{url}/{salida['id']}/anular", json={"motivo": "Marcó por error"}, headers=H))
    assert anulado["anulado"] is True and anulado["motivo_anulacion"] == "Marcó por error" and anulado["anulado_por_nombre"]
    assert estado()["estado"] == "EN_TURNO", "Un marcaje anulado deja de contar"
    assert client.post(f"{url}/{salida['id']}/anular", json={"motivo": "Otra vez"}, headers=H).status_code == 409

    registros = _ok(client.get(url, params={"usuario_id": uid}, headers=H))
    assert len(registros) == 2, "Sigue visible en la bitácora"
    auditoria = _ok(client.get(f"{API}/auditoria/?tabla_afectada=registro_asistencia", headers=H))
    assert any(r["registro_id"] == salida["id"] and r["seccion_consultada"] == "ANULACION_MARCAJE" for r in auditoria)

    # No se puede dejar un orden imposible: una entrada no se quita si hay una salida después
    _marcar(c, "SALIDA")
    entrada = next(r for r in registros if r["tipo_evento"] == "ENTRADA")
    res = client.post(f"{url}/{entrada['id']}/anular", json={"motivo": "x"}, headers=H)
    assert res.status_code == 409 and res.json()["detail"]
    print("✔ Anulación: un marcaje por error deja de contar, sigue visible y no puede dejar un orden imposible.")


def test_correccion_tras_una_anulacion():
    nombre, uid = _usuario()
    c = _cabeceras(nombre)
    _marcar(c, "ENTRADA")
    salida = _marcar(c, "SALIDA")
    _ok(client.post(f"{API}/personal/asistencia/{salida['id']}/anular", json={"motivo": "Hora equivocada"}, headers=H))
    # Corregir la hora: se anula y se agrega la correcta
    _ok(client.post(f"{API}/personal/asistencia/correcciones", json={
        "usuario_id": uid, "tipo_evento": "SALIDA", "fecha_hora": datetime.now(timezone.utc).isoformat(), "motivo": "Hora correcta",
    }, headers=H), 201)
    assert _ok(client.get(f"{API}/auth/fichaje/estado", headers=c))["estado"] == "TURNO_CERRADO"
    print("✔ Corrección: anular y agregar permite corregir la hora de un marcaje.")


if __name__ == "__main__":
    test_una_sola_caja_abierta()
    test_citas_simultaneas()
    test_referencias_inexistentes()
    test_datos_extremos_sin_error_interno()
    test_politica_de_contrasenas()
    test_limite_de_intentos()
    test_cambio_de_contrasena_propia()
    test_cambio_por_administrador_cierra_sesiones()
    test_administrador_no_se_bloquea()
    test_recuperar_acceso_por_terminal()
    test_listados_con_limite()
    test_descanso_completo_en_turno_cerrado()
    test_anular_marcaje_por_error()
    test_correccion_tras_una_anulacion()
    print("TODAS LAS PRUEBAS PASARON")
