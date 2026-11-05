"""Acceso, contraseñas, usuarios y permisos, contra la API de la instalación de producción."""
import re
from uuid import uuid4

import pytest
from apoyo import BASE, CLAVE, CLAVE_INICIAL, dc, sql

caso = pytest.mark.caso
MENSAJE_LOGIN = "Credenciales incorrectas"


def reiniciar_backend():
    """El límite de intentos vive en memoria: reiniciar lo borra."""
    dc("restart", "backend")
    dc("up", "-d", "--wait", "backend")


@pytest.fixture(autouse=True, scope="module")
def limpiar_intentos():
    yield
    reiniciar_backend()


@caso("ACC-02")
def test_clave_incorrecta(fab, sin_sesion):
    u = fab.usuario()
    res = sin_sesion.login(u.alias, "Incorrecta1")
    assert res.status == 401 and MENSAJE_LOGIN in res.detalle


@caso("ACC-03")
def test_usuario_inexistente_no_revela(sin_sesion, fab):
    u = fab.usuario()
    assert sin_sesion.login(f"nadie_{uuid4().hex[:6]}", "x").detalle == sin_sesion.login(u.alias, "x").detalle


@caso("ACC-05", "ACC-06")
def test_bloqueo_tras_fallos(fab, sin_sesion):
    u = fab.usuario()
    assert [sin_sesion.login(u.alias, "Incorrecta1").status for _ in range(5)] == [401] * 5
    res = sin_sesion.login(u.alias, u.clave)
    assert res.status == 429 and "Demasiados intentos" in res.detalle and res.headers.get("retry-after")


@caso("ACC-08")
def test_acierto_reinicia_el_conteo(fab, sin_sesion):
    u = fab.usuario()
    for _ in range(4):
        sin_sesion.login(u.alias, "Incorrecta1")
    assert sin_sesion.login(u.alias, u.clave).status == 200
    assert [sin_sesion.login(u.alias, "Incorrecta1").status for _ in range(4)] == [401] * 4
    assert sin_sesion.login(u.alias, u.clave).status == 200


@caso("ACC-09")
def test_bloqueo_no_afecta_a_otro_usuario(fab, sin_sesion):
    a, b = fab.usuario(), fab.usuario()
    for _ in range(5):
        sin_sesion.login(a.alias, "Incorrecta1")
    assert sin_sesion.login(a.alias, a.clave).status == 429
    assert sin_sesion.login(b.alias, b.clave).status == 200


@caso("ACC-13", "ACC-19", "USU-10")
def test_usuario_desactivado(fab, api, sin_sesion):
    u = fab.usuario()
    assert u.api.get("/auth/me").status == 200
    assert api.put(f"/usuarios/{u.id}", {"activo": False}).ok
    res = sin_sesion.login(u.alias, u.clave)
    assert res.status == 403 and "inactivo" in res.detalle
    assert u.api.get("/auth/me").status == 403
    assert api.put(f"/usuarios/{u.id}", {"activo": True}).ok
    assert sin_sesion.login(u.alias, u.clave).status == 200


@caso("ACC-17", "USU-24")
def test_token_invalido_o_ausente(sin_sesion):
    assert sin_sesion.get("/pacientes/").status == 401
    assert sin_sesion.como("abc.def.ghi").get("/auth/me").status == 401


@caso("ACC-22")
def test_entrar_con_correo(fab, sin_sesion):
    u = fab.usuario()
    assert sin_sesion.login(f"{u.alias}@clinica-pruebas.com", u.clave).status == 200
    assert sin_sesion.login(f"{u.alias}@CLINICA-PRUEBAS.COM", u.clave).status == 200


@caso("ACC-23")
def test_inyeccion_en_login(sin_sesion):
    res = sin_sesion.login("' OR 1=1 --", "x")
    assert res.status == 401 and MENSAJE_LOGIN in res.detalle


@caso("PWD-03", "PWD-04", "PWD-05", "PWD-07", "PWD-08", "PWD-09")
def test_cambio_de_contrasena_propia(fab, sin_sesion):
    u = fab.usuario(cambiar_clave=False)
    url = "/auth/cambiar-contrasena"
    assert u.api.post(url, {"actual": CLAVE_INICIAL, "nueva": "Ab1"}).status == 422
    for debil in ("abcdefgh", "12345678"):
        res = u.api.post(url, {"actual": CLAVE_INICIAL, "nueva": debil})
        assert res.status == 422 and "letras y números" in res.text
    assert u.api.post(url, {"actual": CLAVE_INICIAL, "nueva": "Password123"}).status == 422
    res = u.api.post(url, {"actual": "Mala1234!", "nueva": CLAVE})
    assert res.status == 400 and "actual no es correcta" in res.detalle
    res = u.api.post(url, {"actual": CLAVE_INICIAL, "nueva": CLAVE_INICIAL})
    assert res.status == 400 and "distinta" in res.detalle
    token = u.api.post(url, {"actual": CLAVE_INICIAL, "nueva": CLAVE}).json()["access_token"]
    assert sin_sesion.login(u.alias, CLAVE_INICIAL).status == 401
    assert sin_sesion.login(u.alias, CLAVE).status == 200
    assert sin_sesion.como(token).get("/auth/me").json()["debe_cambiar_contrasena"] is False


@caso("PWD-10")
def test_cambio_cierra_otras_sesiones(fab, sin_sesion):
    u = fab.usuario()
    otra = sin_sesion.como(sin_sesion.login(u.alias, u.clave).json()["access_token"])
    u.api.post("/auth/cambiar-contrasena", {"actual": u.clave, "nueva": "Otra1234!"})
    assert otra.get("/auth/me").status == 401


@caso("PWD-12", "PWD-13")
def test_restablecer_por_administrador(fab, api, sin_sesion):
    u = fab.usuario()
    assert api.put(f"/usuarios/{u.id}", {"telefono": "70000001"}).ok
    assert u.api.get("/auth/me").status == 200
    assert api.put(f"/usuarios/{u.id}", {"password": "Reinicio99!"}).ok
    assert u.api.get("/auth/me").status == 401
    nueva = sin_sesion.como(sin_sesion.login(u.alias, "Reinicio99!").json()["access_token"])
    assert nueva.get("/auth/me").json()["debe_cambiar_contrasena"] is True


@caso("PWD-14")
def test_auditoria_sin_contrasenas(fab):
    u = fab.usuario()
    registros = fab.auditoria("usuarios")
    assert any(r["registro_id"] == u.id and r["seccion_consultada"] == "CAMBIO_CONTRASENA" for r in registros)
    assert CLAVE not in str(registros) and "$2b$" not in str(registros)


@caso("PWD-15")
def test_administrador_no_asigna_debil(fab, api):
    u = fab.usuario()
    res = api.put(f"/usuarios/{u.id}", {"password": "abc"})
    assert res.status == 422
    alias = f"qa_{uuid4().hex[:8]}"
    assert api.post("/usuarios/", {"username": alias, "password": "123", "nombre": "A", "apellido": "B", "email": f"{alias}@clinica-pruebas.com", "rol_id": fab.roles["DOCTOR"]}).status == 422


@caso("PWD-16", "PWD-17", "OPE-18")
def test_recuperar_acceso_por_terminal(fab, api, sin_sesion):
    admin2 = fab.usuario("ADMIN")
    assert api.put(f"/usuarios/{admin2.id}", {"activo": False}).ok
    salida = dc("run", "--rm", "-e", "ADMIN_PASSWORD=Recuperada2026!", "migraciones", "python", "scripts/restablecer_admin.py", admin2.alias)
    assert "restablecido" in salida
    assert admin2.api.get("/auth/me").status == 401
    assert sin_sesion.login(admin2.alias, "Recuperada2026!").status == 200
    assert "No existe un administrador" in dc("run", "--rm", "-e", "ADMIN_PASSWORD=Recuperada2026!", "migraciones", "python", "scripts/restablecer_admin.py", "nadie_x", comprobar=False)
    assert "letras y números" in dc("run", "--rm", "-e", "ADMIN_PASSWORD=abcdefghij", "migraciones", "python", "scripts/restablecer_admin.py", admin2.alias, comprobar=False)


@caso("PWD-18")
def test_api_exige_cambiar_la_contrasena_inicial(fab):
    u = fab.usuario("RECEPCION", cambiar_clave=False)
    res = u.api.get("/pacientes/")
    assert res.status == 403 and "cambiar tu contraseña" in res.detalle
    assert u.api.get("/auth/me").status == 200
    token = u.api.post("/auth/cambiar-contrasena", {"actual": CLAVE_INICIAL, "nueva": CLAVE}).json()["access_token"]
    assert u.api.como(token).get("/pacientes/").status == 200


@caso("USU-01", "USU-02", "USU-03")
def test_crear_cada_rol(fab, api):
    for rol in ("ADMIN", "DOCTOR", "ASISTENTE", "RECEPCION"):
        assert fab.usuario(rol).id
    alias = f"qa_{uuid4().hex[:8]}"
    doctor = api.post("/usuarios/", {
        "username": alias, "password": CLAVE, "nombre": "D", "apellido": "R", "email": f"{alias}@clinica-pruebas.com", "rol_id": fab.roles["DOCTOR"],
        "doctor_perfil": {"especialidad": "Ortodoncia", "numero_colegiatura": "COL-1", "color_agenda": "#112233"},
    }).json()
    perfil = doctor["doctor_perfil"]
    assert perfil["especialidad"] == "Ortodoncia" and perfil["numero_colegiatura"] == "COL-1"
    assert any(d["usuario_id"] == doctor["id"] for d in api.get("/usuarios/doctores/lista").json())
    asistente = fab.usuario("ASISTENTE")
    assert asistente.id in api.get("/usuarios/asistentes/lista").text


@caso("USU-04", "USU-05", "USU-06", "USU-07")
def test_validaciones_de_usuario(fab, api):
    u = fab.usuario()
    base = {"password": CLAVE, "nombre": "A", "apellido": "B", "rol_id": fab.roles["DOCTOR"]}
    res = api.post("/usuarios/", {**base, "username": u.alias, "email": f"{uuid4().hex[:8]}@clinica-pruebas.com"})
    assert res.status == 400 and "ya está en uso" in res.detalle
    res = api.post("/usuarios/", {**base, "username": uuid4().hex[:8], "email": f"{u.alias}@clinica-pruebas.com"})
    assert res.status == 400 and "ya está registrado" in res.detalle
    assert api.post("/usuarios/", {**base, "username": uuid4().hex[:8], "email": "no-es-correo"}).status == 422
    assert api.post("/usuarios/", {"username": uuid4().hex[:8]}).status == 422


@caso("USU-08")
def test_editar_usuario(fab, api):
    u = fab.usuario()
    datos = api.put(f"/usuarios/{u.id}", {"nombre": "Nuevo", "telefono": "71111111", "rol_id": fab.roles["RECEPCION"]}).json()
    assert datos["nombre"] == "Nuevo" and datos["telefono"] == "71111111" and datos["rol_id"] == fab.roles["RECEPCION"]


@caso("USU-11", "USU-12")
def test_administrador_no_se_bloquea(fab, api):
    yo = api.get("/auth/me").json()["id"]
    res = api.put(f"/usuarios/{yo}", {"activo": False})
    assert res.status == 400 and "propia cuenta" in res.detalle
    assert api.put(f"/usuarios/{yo}", {"rol_id": fab.roles["DOCTOR"]}).status == 400
    assert api.get("/auth/me").json()["rol"] == "ADMIN"


@caso("USU-13", "USU-14")
def test_siempre_queda_un_administrador(fab, api):
    otro = fab.usuario("ADMIN")
    assert api.put(f"/usuarios/{otro.id}", {"activo": False}).ok
    # Con varios administradores se puede retirar a otro; el último activo nunca queda fuera
    activos = sql("select u.id from usuarios u join roles r on r.id = u.rol_id where r.codigo = 'ADMIN' and u.activo").split()
    yo = api.get("/auth/me").json()["id"]
    for uid in activos:
        if uid != yo:
            assert api.put(f"/usuarios/{uid}", {"activo": False}).ok
    assert api.put(f"/usuarios/{yo}", {"activo": False}).status == 400
    assert sql("select count(*) from usuarios u join roles r on r.id = u.rol_id where r.codigo = 'ADMIN' and u.activo") == "1"


def _permiso(api, codigo):
    return next(p["id"] for p in api.get("/usuarios/permisos").json() if p["codigo_permiso"] == codigo)


def _rol(api, *codigos):
    res = api.post("/usuarios/roles", {"nombre": f"Rol {uuid4().hex[:8]}", "permiso_ids": [_permiso(api, c) for c in codigos]})
    assert res.status in (200, 201), res.text
    return res.json()["id"]


@caso("USU-15", "USU-16", "USU-17")
def test_rol_personalizado(fab, api):
    rol = _rol(api, "PACIENTES_READ", "REPORTES_READ")
    u = fab.usuario(rol)
    assert u.api.get("/pacientes/").status == 200 and u.api.get("/reportes/resumen-financiero").status == 200
    assert u.api.get("/caja/pagos").status in (403, 404, 405) and u.api.post("/pacientes/", {}).status == 403
    assert api.post(f"/usuarios/roles/{rol}/permisos", [_permiso(api, "REPORTES_READ")]).ok
    assert u.api.get("/pacientes/").status == 403, "El cambio aplica en la siguiente petición"
    assert api.post("/usuarios/roles", {"nombre": "  ", "permiso_ids": []}).status == 422


@caso("USU-18", "USU-19", "USU-20")
def test_sin_escalada_de_privilegios(fab, api):
    rol = _rol(api, "USUARIOS_MANAGE", "ROLES_MANAGE")
    gestor = fab.usuario(rol)
    yo = api.get("/auth/me").json()["id"]
    assert gestor.api.put(f"/usuarios/{yo}", {"password": "Hackeada123!"}).status == 403
    assert gestor.api.put(f"/usuarios/{gestor.id}", {"nombre": "Yo"}).status == 403
    alias = uuid4().hex[:8]
    assert gestor.api.post("/usuarios/", {"username": alias, "password": CLAVE, "nombre": "A", "apellido": "B", "email": f"{alias}@clinica-pruebas.com", "rol_id": fab.roles["ADMIN"]}).status == 403
    assert gestor.api.post(f"/usuarios/roles/{rol}/permisos", [_permiso(api, "CAJA_ANULAR_PAGOS")]).status == 403


RUTAS_PROHIBIDAS = {
    "DOCTOR": [("get", "/caja/estado", None), ("post", "/caja/abrir", {}), ("get", "/auditoria/", None), ("get", "/reportes/resumen-financiero", None), ("get", "/usuarios/", None), ("post", "/sillones/", {}), ("post", "/tratamientos/catalogo", {})],
    "ASISTENTE": [("post", "/pacientes/", {}), ("post", "/citas/", {}), ("post", "/caja/pagos", {}), ("get", "/empleados/pagos/x", None), ("post", "/visitas/", {}), ("post", "/protesis/", {}), ("post", "/odontogramas/", {}), ("get", "/auditoria/", None)],
    "RECEPCION": [("get", "/visitas/", None), ("get", "/odontogramas/", None), ("get", "/radiografias/", None), ("post", "/protesis/", {}), ("post", "/caja/pagos/00000000-0000-0000-0000-000000000000/anular", {"motivo": "x"}), ("get", "/reportes/resumen-financiero", None), ("get", "/auditoria/", None), ("put", "/pacientes/00000000-0000-0000-0000-000000000000/antecedentes", {})],
}


@caso("USU-23")
@pytest.mark.parametrize("rol", RUTAS_PROHIBIDAS)
def test_cada_rol_recibe_403(fab, rol):
    u = fab.usuario(rol)
    for metodo, ruta, cuerpo in RUTAS_PROHIBIDAS[rol]:
        if ruta == "/caja/estado":  # Responde a todos, sin montos: se valida en CAJ-24
            continue
        res = getattr(u.api, metodo)(ruta, cuerpo) if cuerpo is not None else getattr(u.api, metodo)(ruta)
        assert res.status in (403, 404, 405), f"{rol} {metodo} {ruta}: {res.status}"
        if "/x" not in ruta:
            assert res.status == 403, f"{rol} {metodo} {ruta}: {res.status}"


@caso("USU-25")
def test_respuestas_sin_contrasena(api):
    texto = api.get("/usuarios/").text
    assert "password" not in texto and "$2b$" not in texto


@caso("PAC-14", "PAC-20", "PAC-22")
def test_permisos_de_pacientes(fab, api):
    p = fab.paciente()
    rec, asi = fab.usuario("RECEPCION"), fab.usuario("ASISTENTE")
    assert rec.api.put(f"/pacientes/{p['id']}/antecedentes", {"alergias": "x"}).status == 403
    assert asi.api.post("/pacientes/", {}).status == 403 and asi.api.put(f"/pacientes/{p['id']}", {"nombres": "x"}).status == 403
    assert api.delete(f"/pacientes/{p['id']}").status == 405


@caso("SEG-05")
def test_detalles_internos(fab):
    res = fab.admin.post("/pacientes/", {"nombres": "x" * 5000, "apellidos": "B", "tipo_documento": "CI", "numero_documento": f"Q{uuid4().hex[:8]}", "genero": "OTRO", "fecha_nacimiento": "1990-01-01", "telefono": "7"})
    assert res.status == 422 and not re.search(r"psycopg|sqlalchemy|Traceback|INSERT INTO", res.text, re.I)
