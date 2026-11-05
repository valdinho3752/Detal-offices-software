import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import Usuario, Rol, RolCodigoEnum
from app.core.security import hash_password

client = TestClient(app)

def test_hu01_completo():
    print("==================================================")
    print("EJECUTANDO SUITE DE PRUEBAS AUTOMATIZADAS: HU-01")
    print("Gestión de Roles y Asignación de Permisos Granulares")
    print("==================================================")

    # 1. Autenticación como Administrador
    login_admin = client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    assert login_admin.status_code == 200, f"Fallo login admin: {login_admin.text}"
    admin_token = login_admin.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("✔ [Escenario 0] Login de Administrador autenticado exitosamente.")

    # 2. Escenario 1: Listar catálogo de permisos y roles del sistema
    res_permisos = client.get("/api/v1/usuarios/permisos", headers=admin_headers)
    assert res_permisos.status_code == 200
    permisos = res_permisos.json()
    assert len(permisos) >= 35, f"Se esperaban al menos 35 permisos, obtenidos: {len(permisos)}"
    print(f"✔ [Escenario 1] Catálogo de permisos listado correctamente: {len(permisos)} permisos activos.")

    res_roles = client.get("/api/v1/usuarios/roles", headers=admin_headers)
    assert res_roles.status_code == 200
    roles = res_roles.json()
    codigos_roles = [r["codigo"] for r in roles]
    assert "ADMIN" in codigos_roles and "DOCTOR" in codigos_roles and "RECEPCION" in codigos_roles
    print(f"✔ [Escenario 1] Roles del sistema listados: {codigos_roles}")

    # 3. Escenario 2: Creación de un rol personalizado
    # Se usa un rol propio: cambiar los permisos del rol DOCTOR afectaría a los doctores reales
    from uuid import uuid4
    res_rol = client.post("/api/v1/usuarios/roles", json={"nombre": f"Rol prueba {uuid4().hex[:8]}"}, headers=admin_headers)
    assert res_rol.status_code == 201, res_rol.text
    doctor_rol_id = res_rol.json()["id"]

    # 4. Escenario 3: Asignar permisos específicos a un rol
    # Seleccionamos 3 permisos específicos de prueba
    permisos_prueba = [p["id"] for p in permisos if p["codigo_permiso"] in ["PACIENTES_READ", "CITAS_READ", "ODONTOGRAMA_READ"]]
    res_asignacion = client.post(
        f"/api/v1/usuarios/roles/{doctor_rol_id}/permisos",
        json=permisos_prueba,
        headers=admin_headers
    )
    assert res_asignacion.status_code == 200, f"Error asignando permisos: {res_asignacion.text}"
    permisos_actuales = res_asignacion.json()
    assert len(permisos_actuales) == 3
    print(f"✔ [Escenario 3] Permisos granulares asignados al rol con éxito: {[p['codigo_permiso'] for p in permisos_actuales]}")

    # Verificar con GET que los permisos persisten
    res_verificacion = client.get(f"/api/v1/usuarios/roles/{doctor_rol_id}/permisos", headers=admin_headers)
    assert res_verificacion.status_code == 200
    assert len(res_verificacion.json()) == 3
    print("✔ [Escenario 3] Persistencia de permisos en base de datos validada.")

    # 5. Escenario 4: Seguridad y denegación de acceso a usuarios sin rol ADMIN (403 Forbidden)
    # Creamos temporalmente un usuario con rol RECEPCION para probar restricción
    db = SessionLocal()
    try:
        recepcion_rol = db.query(Rol).filter(Rol.codigo == RolCodigoEnum.RECEPCION).first()
        usuario_test = db.query(Usuario).filter(Usuario.username == "recepcionista_test").first()
        if not usuario_test:
            usuario_test = Usuario(
                rol_id=recepcion_rol.id,
                username="recepcionista_test",
                password_hash=hash_password("recep123"),
                nombre="Laura",
                apellido="Recepción",
                email="laura@clinicadental.com",
                activo=True
            )
            db.add(usuario_test)
            db.commit()
    finally:
        db.close()

    # Login como recepcionista
    login_recep = client.post("/api/v1/auth/login", data={"username": "recepcionista_test", "password": "recep123"})
    assert login_recep.status_code == 200
    recep_token = login_recep.json()["access_token"]
    recep_headers = {"Authorization": f"Bearer {recep_token}"}

    # Intento 1: La recepcionista intenta ver el catálogo de permisos administrativos
    intento_permisos = client.get("/api/v1/usuarios/permisos", headers=recep_headers)
    assert intento_permisos.status_code == 403, f"Se esperaba 403, se obtuvo {intento_permisos.status_code}"
    print("✔ [Escenario 4] Restricción cumplida: Usuario no admin recibe 403 Forbidden al consultar permisos.")

    # Intento 2: La recepcionista intenta modificar los permisos de un rol
    intento_modificar = client.post(
        f"/api/v1/usuarios/roles/{doctor_rol_id}/permisos",
        json=permisos_prueba,
        headers=recep_headers
    )
    assert intento_modificar.status_code == 403
    print("✔ [Escenario 4] Restricción cumplida: Usuario no admin recibe 403 Forbidden al intentar modificar permisos.")

    print("\n==================================================")
    print("¡TODOS LOS CRITERIOS DE ACEPTACIÓN DE HU-01 PASARON CON ÉXITO!")
    print("==================================================")

if __name__ == "__main__":
    test_hu01_completo()
