"""
Comprueba los bloqueos reales de cada rol, los roles personalizados, el límite de los cobros,
la privacidad de las comisiones y el catálogo de tratamientos.
Escribe datos: ejecutar contra una base de pruebas.
"""
import os
import random
import sys
from datetime import date, timedelta
from uuid import uuid4

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.database import SessionLocal
from app.main import app
from app.models import Permiso, UsuarioPermisoEspecial

client = TestClient(app)
API = "/api/v1"
ADMIN = "ADMIN"
SESION = "SESION"

# Cada ruta de la API debe figurar aquí: una ruta nueva sin clasificar hace fallar la prueba.
PROTECCION = {
    ("GET", "/auth/me"): SESION,
    ("POST", "/auth/fichar"): "ASISTENCIA_FICHAR",
    ("GET", "/usuarios/roles"): ("USUARIOS_MANAGE", "ROLES_MANAGE"),
    ("POST", "/usuarios/roles"): "ROLES_MANAGE",
    ("GET", "/usuarios/permisos"): ("USUARIOS_MANAGE", "ROLES_MANAGE"),
    ("POST", "/usuarios/roles/{rol_id}/permisos"): "ROLES_MANAGE",
    ("GET", "/usuarios/roles/{rol_id}/permisos"): "ROLES_MANAGE",
    ("GET", "/usuarios/"): "USUARIOS_MANAGE",
    ("POST", "/usuarios/"): "USUARIOS_MANAGE",
    ("GET", "/usuarios/{id}"): "USUARIOS_MANAGE",
    ("PUT", "/usuarios/{id}"): "USUARIOS_MANAGE",
    ("GET", "/usuarios/doctores/lista"): SESION,
    ("POST", "/usuarios/doctores/perfil"): "USUARIOS_MANAGE",
    ("PUT", "/usuarios/doctores/{id}"): "USUARIOS_MANAGE",
    ("GET", "/usuarios/asistentes/lista"): SESION,
    ("POST", "/usuarios/asistentes/perfil"): "USUARIOS_MANAGE",
    ("GET", "/personal/asistencia"): SESION,  # Sin ASISTENCIA_READ_ALL devuelve solo lo propio
    ("GET", "/personal/contratos"): "EMPLEADOS_READ",
    ("POST", "/personal/contratos"): ADMIN,
    ("PUT", "/personal/contratos/{id}"): ADMIN,
    ("GET", "/pacientes/"): "PACIENTES_READ",
    ("POST", "/pacientes/"): "PACIENTES_CREATE",
    ("GET", "/pacientes/{id}"): "PACIENTES_READ",
    ("PUT", "/pacientes/{id}"): "PACIENTES_UPDATE",
    ("GET", "/pacientes/{id}/saldo"): "PACIENTES_READ",
    ("PUT", "/pacientes/{id}/antecedentes"): "ANTECEDENTES_UPDATE",
    ("GET", "/odontogramas/"): "ODONTOGRAMA_READ",
    ("POST", "/odontogramas/"): "ODONTOGRAMA_CREATE",
    ("GET", "/odontogramas/{id}"): "ODONTOGRAMA_READ",
    ("PUT", "/odontogramas/{id}"): "ODONTOGRAMA_UPDATE",
    ("POST", "/odontogramas/{id}/clonar-como-evolucion"): "ODONTOGRAMA_CREATE",
    ("PUT", "/odontogramas/piezas/{id}"): "ODONTOGRAMA_UPDATE",
    ("POST", "/odontogramas/hallazgos"): "ODONTOGRAMA_UPDATE",
    ("PUT", "/odontogramas/hallazgos/{id}"): "ODONTOGRAMA_UPDATE",
    ("DELETE", "/odontogramas/hallazgos/{id}"): "ODONTOGRAMA_DELETE",
    ("GET", "/tratamientos/catalogo"): "TRATAMIENTOS_READ",
    ("POST", "/tratamientos/catalogo"): ADMIN,
    ("PUT", "/tratamientos/catalogo/{id}"): ADMIN,
    ("DELETE", "/tratamientos/catalogo/{id}"): ADMIN,
    ("GET", "/tratamientos/planes"): "TRATAMIENTOS_READ",
    ("POST", "/tratamientos/planes"): "TRATAMIENTOS_CREATE",
    ("GET", "/tratamientos/planes/{id}"): "TRATAMIENTOS_READ",
    ("PUT", "/tratamientos/planes/{id}"): "TRATAMIENTOS_UPDATE",
    ("POST", "/tratamientos/items"): "TRATAMIENTOS_UPDATE",
    ("PUT", "/tratamientos/items/{id}"): "TRATAMIENTOS_UPDATE",
    ("DELETE", "/tratamientos/items/{id}"): "TRATAMIENTOS_UPDATE",
    ("GET", "/citas/"): "CITAS_READ",
    ("POST", "/citas/"): "CITAS_CREATE",
    ("PUT", "/citas/{id}"): "CITAS_UPDATE",
    ("DELETE", "/citas/{id}"): "CITAS_UPDATE",
    ("PATCH", "/citas/{id}/sillon"): "CITAS_SILLON",
    ("GET", "/visitas/"): "HISTORIA_CLINICA_READ",
    ("POST", "/visitas/"): "HISTORIA_CLINICA_CREATE",
    ("GET", "/visitas/{id}"): "HISTORIA_CLINICA_READ",
    ("PUT", "/visitas/{id}"): "HISTORIA_CLINICA_UPDATE",
    ("POST", "/visitas/{id}/observaciones"): "HISTORIA_CLINICA_OBSERVAR",
    ("GET", "/radiografias/"): "RADIOGRAFIAS_READ",
    ("POST", "/radiografias/"): "RADIOGRAFIAS_CREATE",
    ("GET", "/radiografias/{id}"): "RADIOGRAFIAS_READ",
    ("PUT", "/radiografias/{id}"): "RADIOGRAFIAS_CREATE",
    ("DELETE", "/radiografias/{id}"): "RADIOGRAFIAS_DELETE",
    ("GET", "/protesis/"): "PROTESIS_READ",
    ("POST", "/protesis/"): "PROTESIS_CREATE",
    ("PUT", "/protesis/{id}"): "PROTESIS_UPDATE",
    ("GET", "/caja/estado"): SESION,  # Sin CAJA_READ no devuelve montos
    ("POST", "/caja/abrir"): "CAJA_APERTURA",
    ("POST", "/caja/cerrar"): "CAJA_CIERRE",
    ("POST", "/caja/pagos"): "CAJA_PAGOS",
    ("POST", "/caja/egresos"): "CAJA_EGRESOS",
    ("GET", "/empleados/pagos"): SESION,  # Sin EMPLEADOS_READ devuelve solo lo propio
    ("POST", "/empleados/pagos"): "EMPLEADOS_PAGOS",
    ("GET", "/empleados/comisiones-doctor/{doctor_id}"): SESION,  # Solo las propias sin EMPLEADOS_READ
    ("GET", "/auditoria/"): "AUDITORIA_READ",
    ("GET", "/reportes/tratamientos-demanda"): "REPORTES_READ",
    ("GET", "/reportes/productividad-doctores"): "REPORTES_READ",
    ("GET", "/reportes/resumen-financiero"): "REPORTES_READ",
}


def _login(username, password):
    res = client.post(f"{API}/auth/login", data={"username": username, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


H = _login("admin", "admin123")
ROLES = {r["codigo"]: r for r in client.get(f"{API}/usuarios/roles", headers=H).json()}
PERMISOS = {p["codigo_permiso"]: p["id"] for p in client.get(f"{API}/usuarios/permisos", headers=H).json()}


def _crear_usuario(rol_id):
    username = f"perm_{uuid4().hex[:10]}"
    res = client.post(f"{API}/usuarios/", json={
        "username": username, "password": "Clave1234!", "nombre": "Prueba", "apellido": "Permisos",
        "email": f"{username}@clinica-pruebas.com", "rol_id": rol_id,
    }, headers=H)
    assert res.status_code == 201, res.text
    return res.json(), _login(username, "Clave1234!")


def _crear_rol(*codigos):
    res = client.post(f"{API}/usuarios/roles", json={
        "nombre": f"Rol {uuid4().hex[:10]}", "permiso_ids": [PERMISOS[c] for c in codigos],
    }, headers=H)
    assert res.status_code == 201, res.text
    return res.json()


def _asignar(rol_id, *codigos, headers=H):
    return client.post(f"{API}/usuarios/roles/{rol_id}/permisos", json=[PERMISOS[c] for c in codigos], headers=headers)


def _llamar(metodo, ruta, headers):
    # Un cuerpo inválido e identificadores inexistentes pasan por el control de acceso sin modificar datos
    url = API + ruta.replace("{id}", str(uuid4())).replace("{rol_id}", str(uuid4())).replace("{doctor_id}", str(uuid4()))
    if metodo in ("POST", "PUT", "PATCH"):
        return client.request(metodo, url, json=[], headers=headers)
    return client.request(metodo, url, headers=headers)


def _crear_paciente():
    res = client.post(f"{API}/pacientes/", json={
        "nombres": "Permisos", "apellidos": "Prueba", "tipo_documento": "CI",
        "numero_documento": f"PER-{uuid4().hex[:10]}", "genero": "OTRO",
        "fecha_nacimiento": "1990-01-01", "telefono": "70000000",
    }, headers=H)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _plan(paciente_id, costo, estado="APROBADO"):
    plan = client.post(f"{API}/tratamientos/planes", json={"paciente_id": paciente_id, "titulo": "Plan"}, headers=H).json()
    client.put(f"{API}/tratamientos/planes/{plan['id']}", json={"estado": estado, "costo_total": costo}, headers=H)
    return plan["id"]


def _caja_abierta():
    if not client.get(f"{API}/caja/estado", headers=H).json()["caja_abierta"]:
        assert client.post(f"{API}/caja/abrir", json={"monto_inicial_fondo": 100}, headers=H).status_code == 201


def test_todas_las_rutas_estan_clasificadas():
    rutas = {
        (metodo.upper(), ruta[len(API):])
        for ruta, operaciones in app.openapi()["paths"].items() if ruta.startswith(API)
        for metodo in operaciones
    } - {("POST", "/auth/login")}
    assert rutas == set(PROTECCION), f"Diferencias: {rutas ^ set(PROTECCION)}"
    print(f"✔ Las {len(rutas)} rutas de la API tienen una protección definida.")


def test_rol_sin_permisos_no_accede_a_nada():
    _, cabeceras = _crear_usuario(_crear_rol()["id"])
    for (metodo, ruta), proteccion in PROTECCION.items():
        res = _llamar(metodo, ruta, cabeceras)
        if proteccion == SESION:
            assert res.status_code != 403, f"{metodo} {ruta} debe admitir cualquier sesión"
        else:
            assert res.status_code == 403, f"{metodo} {ruta} debería estar bloqueada y devolvió {res.status_code}"
    print("✔ Un rol sin permisos queda bloqueado en todas las rutas protegidas.")


def test_cada_permiso_abre_solo_su_ruta():
    rol = _crear_rol()
    _, cabeceras = _crear_usuario(rol["id"])
    for (metodo, ruta), proteccion in PROTECCION.items():
        if proteccion in (SESION, ADMIN):
            continue
        for codigo in (proteccion,) if isinstance(proteccion, str) else proteccion:
            assert _asignar(rol["id"], codigo).status_code == 200
            assert _llamar(metodo, ruta, cabeceras).status_code != 403, f"{codigo} debería abrir {metodo} {ruta}"
            # Quitar el permiso cierra la ruta de inmediato, sin volver a iniciar sesión
            assert _asignar(rol["id"]).status_code == 200
            assert _llamar(metodo, ruta, cabeceras).status_code == 403, f"Sin {codigo}, {metodo} {ruta} debe bloquearse"
    print("✔ Cada permiso abre su ruta y al quitarlo se bloquea de inmediato.")


def test_rutas_exclusivas_de_admin():
    _, cabeceras = _crear_usuario(_crear_rol(*PERMISOS.keys())["id"])
    for (metodo, ruta), proteccion in PROTECCION.items():
        if proteccion == ADMIN:
            assert _llamar(metodo, ruta, cabeceras).status_code == 403, f"{metodo} {ruta} es exclusiva de ADMIN"
            assert _llamar(metodo, ruta, H).status_code != 403
    print("✔ Catálogo y contratos: bloqueados incluso a un rol con todos los permisos.")


def test_quien_registra_pagos():
    paciente_id = _crear_paciente()
    _plan(paciente_id, 1000)
    _caja_abierta()
    pago = {"paciente_id": paciente_id, "monto": 1, "metodo_pago": "TRANSFERENCIA"}
    url = f"{API}/caja/pagos"

    assert client.post(url, json=pago, headers=H).status_code == 201
    for rol, esperado in (("RECEPCION", 201), ("DOCTOR", 403), ("ASISTENTE", 403)):
        _, cabeceras = _crear_usuario(ROLES[rol]["id"])
        res = client.post(url, json=pago, headers=cabeceras)
        assert res.status_code == esperado, f"{rol}: esperado {esperado}, obtenido {res.status_code} {res.text}"

    # Un rol nuevo solo puede cobrar si se le asigna el permiso
    rol = _crear_rol()
    _, cabeceras = _crear_usuario(rol["id"])
    assert client.post(url, json=pago, headers=cabeceras).status_code == 403
    _asignar(rol["id"], "CAJA_PAGOS")
    assert client.post(url, json=pago, headers=cabeceras).status_code == 201
    assert client.get(f"{API}/usuarios/roles", headers=cabeceras).status_code == 403, "Cobrar no da otros accesos"
    print("✔ Pagos: ADMIN, RECEPCION y roles con CAJA_PAGOS sí; DOCTOR y ASISTENTE no.")


def test_excepciones_individuales():
    usuario, cabeceras = _crear_usuario(ROLES["ASISTENTE"]["id"])
    assert client.get(f"{API}/auditoria/", headers=cabeceras).status_code == 403
    assert client.get(f"{API}/pacientes/", headers=cabeceras).status_code == 200

    db = SessionLocal()
    try:
        def permiso(codigo):
            return db.query(Permiso).filter(Permiso.codigo_permiso == codigo).first().id
        db.add(UsuarioPermisoEspecial(usuario_id=usuario["id"], permiso_id=permiso("AUDITORIA_READ"), concedido=True))
        db.add(UsuarioPermisoEspecial(usuario_id=usuario["id"], permiso_id=permiso("PACIENTES_READ"), concedido=False))
        db.commit()
    finally:
        db.close()
    assert client.get(f"{API}/auditoria/", headers=cabeceras).status_code == 200
    assert client.get(f"{API}/pacientes/", headers=cabeceras).status_code == 403
    print("✔ Las excepciones por usuario conceden y revocan permisos.")


def test_comisiones_privadas():
    doctor_a, cab_a = _crear_usuario(ROLES["DOCTOR"]["id"])
    doctor_b, cab_b = _crear_usuario(ROLES["DOCTOR"]["id"])
    me_a = client.get(f"{API}/auth/me", headers=cab_a).json()
    me_b = client.get(f"{API}/auth/me", headers=cab_b).json()
    url = f"{API}/empleados/comisiones-doctor"

    assert client.get(f"{url}/{me_a['doctor_id']}", headers=cab_a).status_code == 200
    assert client.get(f"{url}/{me_b['doctor_id']}", headers=cab_a).status_code == 403
    assert client.get(f"{url}/{me_a['doctor_id']}", headers=H).status_code == 200
    for rol in ("RECEPCION", "ASISTENTE"):
        _, cabeceras = _crear_usuario(ROLES[rol]["id"])
        assert client.get(f"{url}/{me_a['doctor_id']}", headers=cabeceras).status_code == 403

    # Tampoco se pueden ver los pagos de otro doctor pidiéndolos por identificador
    pago = client.post(f"{API}/empleados/pagos", json={
        "usuario_empleado_id": doctor_b["id"], "tipo_pago": "BONO", "monto_neto_pagado": 7, "metodo_pago": "TRANSFERENCIA",
    }, headers=H)
    assert pago.status_code == 201, pago.text
    vistos = client.get(f"{API}/empleados/pagos?usuario_empleado_id={doctor_b['id']}", headers=cab_a).json()
    assert vistos == [], "Un doctor no debe ver pagos ajenos"
    assert client.post(f"{API}/empleados/pagos", json=[], headers=cab_a).status_code == 403

    # Un rol con permiso de consulta general sí las ve
    _, cabeceras = _crear_usuario(_crear_rol("EMPLEADOS_READ")["id"])
    assert client.get(f"{url}/{me_a['doctor_id']}", headers=cabeceras).status_code == 200

    # La caja no entrega montos a quien no tiene CAJA_READ
    _caja_abierta()
    estado = client.get(f"{API}/caja/estado", headers=cab_a).json()
    assert estado["caja_abierta"] is True and "saldo_en_gaveta" not in estado
    print("✔ Comisiones: cada doctor ve solo las suyas; la gaveta oculta los montos.")


def test_rol_personalizado_clinico():
    res = client.post(f"{API}/usuarios/roles", json={"nombre": "Coordinación Clínica " + uuid4().hex[:6], "descripcion": "Prueba"}, headers=H)
    assert res.status_code == 201, res.text
    rol = res.json()
    assert rol["codigo"].startswith("COORDINACION_CLINICA_") and rol["permisos"] == [] and rol["es_sistema"] is False

    assert _asignar(rol["id"], "TRATAMIENTOS_CREATE", "CITAS_CREATE", "PROTESIS_CREATE").status_code == 200
    listado = next(r for r in client.get(f"{API}/usuarios/roles", headers=H).json() if r["id"] == rol["id"])
    assert {p["codigo_permiso"] for p in listado["permisos"]} == {"TRATAMIENTOS_CREATE", "CITAS_CREATE", "PROTESIS_CREATE"}

    usuario, cabeceras = _crear_usuario(rol["id"])
    me = client.get(f"{API}/auth/me", headers=cabeceras).json()
    assert set(me["permisos"]) == {"TRATAMIENTOS_CREATE", "CITAS_CREATE", "PROTESIS_CREATE"}

    # Sin perfil médico debe indicar el doctor responsable, y no se convierte en doctor
    paciente_id, doctor = _crear_paciente(), client.get(f"{API}/usuarios/doctores/lista", headers=H).json()[0]
    assert client.post(f"{API}/tratamientos/planes", json={"paciente_id": paciente_id, "titulo": "Sin doctor"}, headers=cabeceras).status_code == 400
    plan = client.post(f"{API}/tratamientos/planes", json={"paciente_id": paciente_id, "doctor_id": doctor["id"], "titulo": "Con doctor"}, headers=cabeceras)
    assert plan.status_code == 201 and plan.json()["doctor_id"] == doctor["id"], plan.text
    assert client.get(f"{API}/auth/me", headers=cabeceras).json()["doctor_id"] is None
    print("✔ Rol nuevo: se crea desde el formulario y aplica exactamente sus permisos.")


def test_no_hay_escalada_de_privilegios():
    # Un código no puede hacerse pasar por el rol de administrador
    assert client.post(f"{API}/usuarios/roles", json={"nombre": "x", "codigo": " admin "}, headers=H).status_code == 400
    assert client.post(f"{API}/usuarios/roles", json={"nombre": "Admin"}, headers=H).status_code == 400

    rol_gestor = _crear_rol("ROLES_MANAGE", "USUARIOS_MANAGE")
    usuario, cabeceras = _crear_usuario(rol_gestor["id"])
    otro = _crear_rol()

    assert _asignar(otro["id"], "ROLES_MANAGE", headers=cabeceras).status_code == 200, "Puede otorgar lo que tiene"
    assert _asignar(otro["id"], "CAJA_PAGOS", headers=cabeceras).status_code == 403, "No puede otorgar lo que no tiene"
    assert _asignar(rol_gestor["id"], "CAJA_PAGOS", headers=cabeceras).status_code == 403, "No puede ampliar su propio rol"
    assert _asignar(ROLES["ADMIN"]["id"], "CAJA_PAGOS", headers=cabeceras).status_code == 403
    assert client.post(f"{API}/usuarios/roles", json={"nombre": uuid4().hex[:8], "permiso_ids": [PERMISOS["AUDITORIA_READ"]]}, headers=cabeceras).status_code == 403

    datos = {
        "username": uuid4().hex[:10], "password": "Clave1234!", "nombre": "A", "apellido": "B",
        "email": f"{uuid4().hex[:10]}@clinica-pruebas.com", "rol_id": ROLES["ADMIN"]["id"],
    }
    assert client.post(f"{API}/usuarios/", json=datos, headers=cabeceras).status_code == 403
    assert client.put(f"{API}/usuarios/{usuario['id']}", json={"rol_id": ROLES["ADMIN"]["id"]}, headers=cabeceras).status_code == 403
    admin_id = client.get(f"{API}/auth/me", headers=H).json()["id"]
    assert client.put(f"{API}/usuarios/{admin_id}", json={"password": "Hackeada123!"}, headers=cabeceras).status_code == 403
    print("✔ Sin escalada: nadie se otorga más permisos ni se convierte en administrador.")


def test_limite_de_cobros():
    _caja_abierta()
    url = f"{API}/caja/pagos"

    def cobrar(paciente_id, monto, **extra):
        return client.post(url, json={"paciente_id": paciente_id, "monto": monto, "metodo_pago": "TRANSFERENCIA", **extra}, headers=H)

    def saldo(paciente_id):
        return client.get(f"{API}/pacientes/{paciente_id}/saldo", headers=H).json()["saldo_pendiente"]

    # Sin plan aprobado no hay nada que cobrar
    paciente_id = _crear_paciente()
    assert cobrar(paciente_id, 10).status_code == 400
    propuesto = _plan(paciente_id, 500, "PROPUESTO")
    assert cobrar(paciente_id, 10).status_code == 400
    assert cobrar(paciente_id, 10, plan_id=propuesto).status_code == 400

    # Con plan aprobado se puede adelantar hasta el saldo, nunca más
    plan_id = _plan(paciente_id, 500)
    res = cobrar(paciente_id, "500.01")
    assert res.status_code == 400 and "500.00" in res.json()["detail"], res.text
    assert cobrar(paciente_id, 200).status_code == 201
    assert saldo(paciente_id) == 300.0
    assert cobrar(paciente_id, 301).status_code == 400
    assert cobrar(paciente_id, 300, plan_id=plan_id).status_code == 201
    assert saldo(paciente_id) == 0.0
    assert cobrar(paciente_id, "0.01").status_code == 400

    # El límite también aplica a cada plan y exige que sea del mismo paciente
    otro = _crear_paciente()
    plan_a, plan_b = _plan(otro, 100), _plan(otro, 900)
    assert cobrar(otro, 150, plan_id=plan_a).status_code == 400
    assert cobrar(otro, 100, plan_id=plan_a).status_code == 201
    assert cobrar(_crear_paciente(), 10, plan_id=plan_b).status_code == 404
    assert cobrar(str(uuid4()), 10).status_code == 404
    print("✔ Cobros: un pago o adelanto nunca supera el saldo de los planes aprobados.")


def _cita(paciente_id, doctor_id, headers=H):
    dia = date(2031, 1, 1) + timedelta(days=random.randint(0, 18000))
    return client.post(f"{API}/citas/", json={
        "paciente_id": paciente_id, "doctor_id": doctor_id, "motivo_consulta": "Prueba",
        "fecha_inicio_programada": f"{dia}T09:00:00Z", "fecha_fin_programada": f"{dia}T10:00:00Z",
    }, headers=headers)


def test_citas_entre_doctores():
    _, cab_a = _crear_usuario(ROLES["DOCTOR"]["id"])
    _, cab_b = _crear_usuario(ROLES["DOCTOR"]["id"])
    doc_a = client.get(f"{API}/auth/me", headers=cab_a).json()["doctor_id"]
    doc_b = client.get(f"{API}/auth/me", headers=cab_b).json()["doctor_id"]
    paciente_id = _crear_paciente()

    def nueva_cita_de_b():
        res = _cita(paciente_id, doc_b)
        assert res.status_code == 201, res.text
        return res.json()["id"]

    # El doctor A no puede cambiar nada de una cita del doctor B
    ajena = nueva_cita_de_b()
    assert client.put(f"{API}/citas/{ajena}", json={"motivo_consulta": "Cambiada"}, headers=cab_a).status_code == 403
    assert client.put(f"{API}/citas/{ajena}", json={"doctor_id": doc_a}, headers=cab_a).status_code == 403
    assert client.patch(f"{API}/citas/{ajena}/sillon", json={"estado": "EN_ESPERA"}, headers=cab_a).status_code == 403
    assert client.delete(f"{API}/citas/{ajena}", headers=cab_a).status_code == 403
    guardada = next(c for c in client.get(f"{API}/citas/?paciente_id={paciente_id}", headers=H).json() if c["id"] == ajena)
    assert guardada["motivo_consulta"] == "Prueba" and guardada["estado"] == "PROGRAMADA"
    # Pero sí puede verla, y agendar a otro doctor sigue bloqueado
    assert ajena in [c["id"] for c in client.get(f"{API}/citas/?paciente_id={paciente_id}", headers=cab_a).json()]
    assert _cita(paciente_id, doc_b, headers=cab_a).status_code == 403

    # El doctor dueño sí puede
    assert client.put(f"{API}/citas/{ajena}", json={"motivo_consulta": "Propia"}, headers=cab_b).status_code == 200
    assert client.patch(f"{API}/citas/{ajena}/sillon", json={"estado": "EN_ESPERA"}, headers=cab_b).status_code == 200
    assert client.delete(f"{API}/citas/{ajena}", headers=cab_b).status_code == 204

    # Asistente, recepción y administrador pueden cambiar las de cualquiera
    otros = [_crear_usuario(ROLES[r]["id"])[1] for r in ("ASISTENTE", "RECEPCION")] + [H]
    for cabeceras in otros:
        cita_id = nueva_cita_de_b()
        assert client.put(f"{API}/citas/{cita_id}", json={"motivo_consulta": "Reagendada"}, headers=cabeceras).status_code == 200
        assert client.patch(f"{API}/citas/{cita_id}/sillon", json={"estado": "EN_ESPERA"}, headers=cabeceras).status_code == 200
        assert client.put(f"{API}/citas/{cita_id}", json={"doctor_id": doc_a}, headers=cabeceras).status_code == 200
        assert client.delete(f"{API}/citas/{cita_id}", headers=cabeceras).status_code == 204
    print("✔ Citas: un doctor solo cambia las suyas; asistente, recepción y admin, todas.")


def test_cobro_directo():
    _caja_abierta()
    url = f"{API}/caja/pagos"
    doctor = client.get(f"{API}/usuarios/doctores/lista", headers=H).json()[0]["id"]

    def directo(paciente_id, monto=40, **extra):
        return client.post(url, json={
            "paciente_id": paciente_id, "monto": monto, "metodo_pago": "TRANSFERENCIA",
            "es_cobro_directo": True, "observaciones": "Consulta general", **extra,
        }, headers=H)

    def saldo(paciente_id):
        return client.get(f"{API}/pacientes/{paciente_id}/saldo", headers=H).json()

    # Sin ningún plan, o con el plan solo propuesto, se puede cobrar la consulta
    paciente_id = _crear_paciente()
    assert directo(paciente_id).status_code == 201
    propuesto = _plan(paciente_id, 500, "PROPUESTO")
    assert directo(paciente_id).status_code == 201
    datos = saldo(paciente_id)
    assert datos["saldo_pendiente"] == 0 and datos["total_pagado"] == 0 and datos["estado_saldo"] == "AL_DIA"
    assert [p["es_cobro_directo"] for p in datos["pagos"]] == [True, True]

    # El plan propuesto sigue sin poder cobrarse como abono
    abono = {"paciente_id": paciente_id, "monto": 10, "metodo_pago": "TRANSFERENCIA"}
    assert client.post(url, json=abono, headers=H).status_code == 400
    assert client.post(url, json={**abono, "plan_id": propuesto}, headers=H).status_code == 400

    # Si luego aprueba un plan, lo cobrado por la consulta no descuenta su deuda
    _plan(paciente_id, 300)
    assert saldo(paciente_id)["saldo_pendiente"] == 300
    assert client.post(url, json={**abono, "monto": 301}, headers=H).status_code == 400
    assert directo(paciente_id, monto=1000).status_code == 201, "El límite del saldo no aplica a una consulta"
    assert saldo(paciente_id)["saldo_pendiente"] == 300

    # Debe tener concepto, un monto válido y no apuntar a un plan
    assert directo(paciente_id, observaciones="   ").status_code == 400
    assert directo(paciente_id, monto=0).status_code == 422
    assert directo(paciente_id, plan_id=propuesto).status_code == 400
    assert directo(str(uuid4())).status_code == 404

    # Sigue las reglas de caja y comisión de cualquier cobro
    antes = client.get(f"{API}/caja/estado", headers=H).json()["saldo_en_gaveta"]
    comision = client.get(f"{API}/empleados/comisiones-doctor/{doctor}", headers=H).json()["total_cobrado_por_sus_tratamientos"]
    assert directo(paciente_id, monto=25, metodo_pago="EFECTIVO", doctor_comision_id=doctor).status_code == 201
    assert client.get(f"{API}/caja/estado", headers=H).json()["saldo_en_gaveta"] == antes + 25
    assert client.get(f"{API}/empleados/comisiones-doctor/{doctor}", headers=H).json()["total_cobrado_por_sus_tratamientos"] == comision + 25
    _, doctor_cab = _crear_usuario(ROLES["DOCTOR"]["id"])
    assert client.post(url, json={**abono, "es_cobro_directo": True, "observaciones": "x"}, headers=doctor_cab).status_code == 403
    print("✔ Cobro directo: sin plan, con concepto, y sin alterar el saldo de los planes.")


def test_anticipos_se_descuentan():
    _caja_abierta()
    usuario, cabeceras = _crear_usuario(ROLES["DOCTOR"]["id"])
    doctor_id = client.get(f"{API}/auth/me", headers=cabeceras).json()["doctor_id"]
    assert client.post(f"{API}/personal/contratos", json={
        "usuario_id": usuario["id"], "tipo_remuneracion": "PORCENTAJE_COMISION", "porcentaje_comision": 40,
    }, headers=H).status_code == 201
    paciente_id = _crear_paciente()
    assert client.post(f"{API}/caja/pagos", json={
        "paciente_id": paciente_id, "monto": 1000, "metodo_pago": "TRANSFERENCIA",
        "es_cobro_directo": True, "observaciones": "Consulta", "doctor_comision_id": doctor_id,
    }, headers=H).status_code == 201

    def comisiones():
        return client.get(f"{API}/empleados/comisiones-doctor/{doctor_id}", headers=cabeceras).json()

    def pagar(tipo, monto, **extra):
        res = client.post(f"{API}/empleados/pagos", json={
            "usuario_empleado_id": usuario["id"], "tipo_pago": tipo, "monto_neto_pagado": monto,
            "metodo_pago": "TRANSFERENCIA", **extra,
        }, headers=H)
        assert res.status_code == 201, res.text

    assert comisiones()["saldo_comision_por_pagar"] == 400
    pagar("ADELANTO", 100)
    datos = comisiones()
    assert datos["total_anticipos"] == 100 and datos["saldo_comision_por_pagar"] == 300

    # Liquidar el neto deja el saldo en cero, sin descontar el anticipo dos veces
    pagar("COMISION_TRATAMIENTOS", 300, monto_comisiones=300)
    datos = comisiones()
    assert datos["comisiones_ya_liquidadas"] == 300 and datos["total_anticipos"] == 100
    assert datos["saldo_comision_por_pagar"] == 0

    # Un bono o sueldo no se descuenta de las comisiones
    pagar("BONO", 50)
    assert comisiones()["saldo_comision_por_pagar"] == 0
    print("✔ Anticipos: se descuentan una sola vez de las comisiones del doctor.")


def test_catalogo_de_tratamientos():
    url = f"{API}/tratamientos/catalogo"
    _, doctor = _crear_usuario(ROLES["DOCTOR"]["id"])
    datos = {"codigo": f"CAT-{uuid4().hex[:8]}", "categoria": "ENDODONCIA", "nombre": "Endodoncia de prueba", "costo_base": 120, "duracion_estimada_min": 45}

    assert client.post(url, json=datos, headers=doctor).status_code == 403
    assert client.post(url, json={**datos, "costo_base": -1}, headers=H).status_code == 422
    assert client.post(url, json={**datos, "duracion_estimada_min": 0}, headers=H).status_code == 422
    assert client.post(url, json={**datos, "nombre": "  "}, headers=H).status_code == 422
    res = client.post(url, json=datos, headers=H)
    assert res.status_code == 201, res.text
    item = res.json()
    assert client.post(url, json=datos, headers=H).status_code == 400, "Código duplicado"
    assert client.get(url, headers=doctor).status_code == 200, "Los doctores siguen viendo el catálogo"

    # Actualizar, con auditoría del precio anterior y el nuevo
    assert client.put(f"{url}/{item['id']}", json={"costo_base": 150}, headers=doctor).status_code == 403
    assert client.put(f"{url}/{item['id']}", json={"costo_base": -5}, headers=H).status_code == 422
    res = client.put(f"{url}/{item['id']}", json={"costo_base": 150, "nombre": "Endodoncia actualizada"}, headers=H)
    assert res.status_code == 200 and res.json()["nombre"] == "Endodoncia actualizada", res.text
    logs = client.get(f"{API}/auditoria/?tabla_afectada=catalogo_tratamientos&accion=UPDATE", headers=H).json()
    log = next(l for l in logs if l["registro_id"] == item["id"])
    assert log["datos_previos"]["costo_base"] == "120.00" and log["datos_nuevos"]["costo_base"] == "150"

    otro = client.post(url, json={**datos, "codigo": f"CAT-{uuid4().hex[:8]}"}, headers=H).json()
    assert client.put(f"{url}/{otro['id']}", json={"codigo": datos["codigo"]}, headers=H).status_code == 400

    # Sin uso: se elimina
    assert client.delete(f"{url}/{otro['id']}", headers=doctor).status_code == 403
    res = client.delete(f"{url}/{otro['id']}", headers=H)
    assert res.status_code == 200 and res.json()["resultado"] == "ELIMINADO"
    assert otro["id"] not in [t["id"] for t in client.get(f"{url}?activo_solo=false", headers=H).json()]
    assert client.delete(f"{url}/{otro['id']}", headers=H).status_code == 404

    # En uso: se desactiva, deja de ofrecerse y los planes conservan su nombre y precio
    paciente_id = _crear_paciente()
    plan = client.post(f"{API}/tratamientos/planes", json={"paciente_id": paciente_id, "titulo": "Plan"}, headers=H).json()
    item_plan = client.post(f"{API}/tratamientos/items", json={"plan_id": plan["id"], "tratamiento_id": item["id"], "costo_acordado": 100}, headers=H)
    assert item_plan.status_code == 201, item_plan.text
    res = client.delete(f"{url}/{item['id']}", headers=H)
    assert res.status_code == 200 and res.json()["resultado"] == "DESACTIVADO", res.text
    assert item["id"] not in [t["id"] for t in client.get(url, headers=H).json()]
    assert item["id"] in [t["id"] for t in client.get(f"{url}?activo_solo=false", headers=H).json()]
    conservado = client.get(f"{API}/tratamientos/planes/{plan['id']}", headers=H).json()["items"][0]
    assert conservado["tratamiento"]["nombre"] == "Endodoncia actualizada" and float(conservado["costo_acordado"]) == 100

    res = client.put(f"{url}/{item['id']}", json={"activo": True}, headers=H)
    assert res.status_code == 200 and res.json()["activo"] is True
    assert item["id"] in [t["id"] for t in client.get(url, headers=H).json()]
    print("✔ Catálogo: agregar, actualizar y eliminar solo para ADMIN, sin perder el historial.")


if __name__ == "__main__":
    test_todas_las_rutas_estan_clasificadas()
    test_rol_sin_permisos_no_accede_a_nada()
    test_cada_permiso_abre_solo_su_ruta()
    test_rutas_exclusivas_de_admin()
    test_quien_registra_pagos()
    test_excepciones_individuales()
    test_comisiones_privadas()
    test_rol_personalizado_clinico()
    test_no_hay_escalada_de_privilegios()
    test_limite_de_cobros()
    test_citas_entre_doctores()
    test_cobro_directo()
    test_anticipos_se_descuentan()
    test_catalogo_de_tratamientos()
    print("TODAS LAS PRUEBAS DE PERMISOS PASARON")
