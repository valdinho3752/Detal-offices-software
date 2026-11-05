import sys
import os
from datetime import datetime, timezone, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_hu13_completo():
    print("==================================================")
    print("EJECUTANDO SUITE DE PRUEBAS AUTOMATIZADAS: HU-13")
    print("Panel de Auditoría Forense y Trazabilidad")
    print("==================================================")

    # 1. Login como Administrador
    login_admin = client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    assert login_admin.status_code == 200
    token_admin = login_admin.json()["access_token"]
    headers_admin = {"Authorization": f"Bearer {token_admin}"}
    admin_id = client.get("/api/v1/auth/me", headers=headers_admin).json()["id"]
    print("✔ [Escenario 0] Admin autenticado con éxito.")

    # 2. Control de Acceso: Empleado no-admin es bloqueado (403 Forbidden)
    # Login como Asistente
    asist_login = client.post("/api/v1/auth/login", data={"username": "asist_hu06_fichaje", "password": "AsistPassword123"})
    if asist_login.status_code == 200:
        token_asist = asist_login.json()["access_token"]
        headers_asist = {"Authorization": f"Bearer {token_asist}"}
        res_bloqueo = client.get("/api/v1/auditoria/", headers=headers_asist)
        assert res_bloqueo.status_code == 403, f"Se esperaba 403 Forbidden para no-admin, obtenido: {res_bloqueo.status_code}"
        print("✔ [Escenario 0.1] Control de seguridad RBAC verificado: Acceso al panel de auditoría restringido a ADMIN (HTTP 403).")

    # 3. Obtener un Paciente para las pruebas
    pacientes_res = client.get("/api/v1/pacientes/", headers=headers_admin).json()
    assert len(pacientes_res) > 0
    paciente_target = pacientes_res[0]
    paciente_id = paciente_target["id"]

    # =========================================================================
    # ESCENARIO 1: Trazabilidad de consultas de lectura médica (Acción VIEW)
    # =========================================================================
    # Al abrir el expediente del paciente se debe emitir un log VIEW
    res_get_paciente = client.get(f"/api/v1/pacientes/{paciente_id}", headers=headers_admin)
    assert res_get_paciente.status_code == 200

    # Consultar auditoría filtrando por accion=VIEW
    res_audit_view = client.get("/api/v1/auditoria/?accion=VIEW", headers=headers_admin)
    assert res_audit_view.status_code == 200
    logs_view = res_audit_view.json()
    assert len(logs_view) > 0

    log_paciente_view = next((l for l in logs_view if l["registro_id"] == paciente_id and l["tabla_afectada"] == "pacientes"), None)
    assert log_paciente_view is not None, "Debe existir un log VIEW para la apertura del expediente del paciente"
    assert log_paciente_view["accion"] == "VIEW"
    assert log_paciente_view["usuario_nombre"] is not None
    assert log_paciente_view["fecha_hora"] is not None
    assert log_paciente_view["seccion_consultada"] in ["FICHA_DATOS_PERSONALES", "EXPEDIENTE_CLINICO"]
    print(f"✔ [Escenario 1] Trazabilidad VIEW verificada: Consulta registrada para usuario '{log_paciente_view['usuario_nombre']}' en sección '{log_paciente_view['seccion_consultada']}'.")

    # =========================================================================
    # ESCENARIO 2: Auditoría de cambios críticos (Datos Previos vs Nuevos en JSONB)
    # =========================================================================
    telefono_antiguo = paciente_target.get("telefono")
    nuevo_telefono = "+59179988776"
    nueva_direccion = "Av. Las Palmeras #554, Edificio Los Pinos"

    res_modificar = client.put(f"/api/v1/pacientes/{paciente_id}", json={
        "telefono": nuevo_telefono,
        "direccion": nueva_direccion
    }, headers=headers_admin)
    assert res_modificar.status_code == 200

    # Buscar el log de actualización
    res_audit_update = client.get(f"/api/v1/auditoria/?tabla_afectada=pacientes&accion=UPDATE", headers=headers_admin)
    assert res_audit_update.status_code == 200
    logs_update = res_audit_update.json()
    log_update = next((l for l in logs_update if l["registro_id"] == paciente_id), None)
    assert log_update is not None, "Debe existir el log UPDATE de modificación del paciente"
    assert log_update["datos_previos"] is not None
    assert log_update["datos_nuevos"] is not None
    assert log_update["datos_nuevos"]["telefono"] == nuevo_telefono
    assert log_update["datos_nuevos"]["direccion"] == nueva_direccion
    print(f"✔ [Escenario 2] Auditoría de cambios validada: JSONB previo vs nuevo capturado (Tel: {log_update['datos_previos'].get('telefono')} -> {nuevo_telefono}).")

    # =========================================================================
    # ESCENARIO 3: Filtros combinados del panel de auditoría
    # =========================================================================
    # 3.1 Filtro por usuario_id
    res_filtro_user = client.get(f"/api/v1/auditoria/?usuario_id={admin_id}", headers=headers_admin)
    assert res_filtro_user.status_code == 200
    assert all(l["usuario_id"] == admin_id for l in res_filtro_user.json())
    print(f"✔ [Escenario 3.1] Filtro por usuario_id={admin_id} verificado ({len(res_filtro_user.json())} logs).")

    # 3.2 Filtro por tabla afectada
    res_filtro_tabla = client.get("/api/v1/auditoria/?tabla_afectada=pacientes", headers=headers_admin)
    assert res_filtro_tabla.status_code == 200
    assert all(l["tabla_afectada"] == "pacientes" for l in res_filtro_tabla.json())
    print("✔ [Escenario 3.2] Filtro por tabla_afectada='pacientes' verificado.")

    # 3.3 Filtro por rango de fechas
    ahora = datetime.now(timezone.utc)
    desde = (ahora - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    hasta = (ahora + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    res_filtro_fechas = client.get(f"/api/v1/auditoria/?fecha_desde={desde}&fecha_hasta={hasta}", headers=headers_admin)
    assert res_filtro_fechas.status_code == 200
    assert len(res_filtro_fechas.json()) >= 3
    print("✔ [Escenario 3.3] Filtro por rango temporal verificado.")

    print("\n==================================================")
    print("TODAS LAS PRUEBAS DE HU-13 PASARON CON ÉXITO")
    print("==================================================")

if __name__ == "__main__":
    test_hu13_completo()
