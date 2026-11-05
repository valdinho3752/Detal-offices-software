import sys
import os
from decimal import Decimal
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_hu12_completo():
    print("==================================================")
    print("EJECUTANDO SUITE DE PRUEBAS AUTOMATIZADAS: HU-12")
    print("Nómina, Liquidación de Sueldos y Comisiones")
    print("==================================================")

    # 1. Login como Administrador
    login_admin = client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    assert login_admin.status_code == 200
    token_admin = login_admin.json()["access_token"]
    headers_admin = {"Authorization": f"Bearer {token_admin}"}
    print("✔ [Escenario 0] Admin autenticado con éxito.")

    # 2. Setup: Crear doctor exclusivo para esta prueba de comisiones
    roles_res = client.get("/api/v1/usuarios/roles", headers=headers_admin)
    rol_doctor_id = next(r["id"] for r in roles_res.json() if r["codigo"] == "DOCTOR")

    doc_username = "dr_hu12_comisiones"
    doc_password = "DoctorPassword123"
    doc_login = client.post("/api/v1/auth/login", data={"username": doc_username, "password": doc_password})
    if doc_login.status_code != 200:
        res_u = client.post("/api/v1/usuarios/", json={
            "rol_id": rol_doctor_id,
            "username": doc_username,
            "password": doc_password,
            "nombre": "Mauricio",
            "apellido": "Sandoval",
            "email": "dr_hu12@clinica.com",
            "telefono": "+59178899001",
            "doctor_perfil": {
                "especialidad": "Implantología y Rehabilitación",
                "numero_colegiatura": "COL-HU12-998"
            }
        }, headers=headers_admin)
        assert res_u.status_code == 201
        u_data = res_u.json()
        doc_user_id = u_data["id"]
        doctor_id = u_data["doctor_perfil"]["id"]
    else:
        doc_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {doc_login.json()['access_token']}"}).json()
        doc_user_id = doc_me["id"]
        doctores_list = client.get("/api/v1/usuarios/doctores/lista", headers=headers_admin).json()
        doctor_id = next(d["id"] for d in doctores_list if d["usuario_id"] == doc_user_id)

    # Asegurar contrato de remuneración al 40.00%
    contratos = client.get("/api/v1/personal/contratos", headers=headers_admin).json()
    tiene_contrato = any(c["usuario_id"] == doc_user_id for c in contratos)
    if not tiene_contrato:
        client.post("/api/v1/personal/contratos", json={
            "usuario_id": doc_user_id,
            "tipo_remuneracion": "PORCENTAJE_COMISION",
            "porcentaje_comision": 40.00,
            "salario_base": 0.00
        }, headers=headers_admin)

    print(f"✔ [Setup] Doctor listo (Usuario: {doc_user_id}, Doctor: {doctor_id}, Comisión: 40%).")

    # 3. Setup de Caja y Pagos acumulados de $3,000.00 asignados a este doctor
    estado_caja = client.get("/api/v1/caja/estado", headers=headers_admin).json()
    if not estado_caja.get("caja_abierta"):
        client.post("/api/v1/caja/abrir", json={"monto_inicial_fondo": 500.00, "observaciones": "Caja para HU-12"}, headers=headers_admin)

    pacientes_res = client.get("/api/v1/pacientes/", headers=headers_admin).json()
    paciente_id = pacientes_res[0]["id"]
    # Los cobros no pueden superar el saldo: el paciente necesita un plan aprobado
    plan_saldo = client.post("/api/v1/tratamientos/planes", json={
        "paciente_id": paciente_id, "titulo": "Plan con saldo para cobros"
    }, headers=headers_admin).json()
    client.put(f"/api/v1/tratamientos/planes/{plan_saldo['id']}", json={"estado": "APROBADO", "costo_total": 5000}, headers=headers_admin)


    # Simulamos 2 cobros de $1,500.00 c/u asociados al doctor = $3,000.00
    client.post("/api/v1/caja/pagos", json={
        "paciente_id": paciente_id,
        "doctor_comision_id": doctor_id,
        "monto": 1500.00,
        "metodo_pago": "TRANSFERENCIA",
        "referencia_comprobante": "TRF-HU12-01",
        "observaciones": "Implante pieza 21 fase 1"
    }, headers=headers_admin)

    client.post("/api/v1/caja/pagos", json={
        "paciente_id": paciente_id,
        "doctor_comision_id": doctor_id,
        "monto": 1500.00,
        "metodo_pago": "TRANSFERENCIA",
        "referencia_comprobante": "TRF-HU12-02",
        "observaciones": "Implante pieza 21 fase 2"
    }, headers=headers_admin)
    print("✔ [Setup] Registrados $3,000.00 de producción cobrada para el doctor.")

    # =========================================================================
    # ESCENARIO 1: Cálculo automatizado de comisiones por doctor (40% de $3,000 = $1,200)
    # =========================================================================
    res_comision = client.get(f"/api/v1/empleados/comisiones-doctor/{doctor_id}", headers=headers_admin)
    assert res_comision.status_code == 200, f"Error calculando comisiones: {res_comision.text}"
    com_data = res_comision.json()
    assert com_data["porcentaje_pactado"] == 40.0
    assert com_data["total_cobrado_por_sus_tratamientos"] >= 3000.0
    assert com_data["comision_bruta_generada"] >= 1200.0
    com_bruta_ini = com_data["comision_bruta_generada"]
    com_ya_pagada_ini = com_data["comisiones_ya_liquidadas"]
    saldo_ini = com_data["saldo_comision_por_pagar"]
    print(f"✔ [Escenario 1] Comisiones calculadas: Producción: ${com_data['total_cobrado_por_sus_tratamientos']:.2f}, Bruta (40%): ${com_bruta_ini:.2f}, Pendiente: ${saldo_ini:.2f}.")

    # =========================================================================
    # ESCENARIO 2: Pago de anticipo en efectivo desde la caja diaria (Adelanto)
    # =========================================================================
    estado_caja_antes = client.get("/api/v1/caja/estado", headers=headers_admin).json()
    egresos_caja_antes = estado_caja_antes["total_egresos_efectivo"]

    adelanto_payload = {
        "usuario_empleado_id": doc_user_id,
        "tipo_pago": "ADELANTO",
        "monto_neto_pagado": 200.00,
        "metodo_pago": "EFECTIVO_CAJA",
        "observaciones": "Adelanto quincenal solicitado por el doctor"
    }
    res_adelanto = client.post("/api/v1/empleados/pagos", json=adelanto_payload, headers=headers_admin)
    assert res_adelanto.status_code == 201, f"Error registrando adelanto: {res_adelanto.text}"
    adelanto_data = res_adelanto.json()
    adelanto_id = adelanto_data["id"]
    assert adelanto_data["tipo_pago"] == "ADELANTO"

    # Verificar que en caja se debitó automáticamente
    estado_caja_despues = client.get("/api/v1/caja/estado", headers=headers_admin).json()
    esperado_egresos = egresos_caja_antes + 200.00
    assert abs(estado_caja_despues["total_egresos_efectivo"] - esperado_egresos) < 0.01
    print(f"✔ [Escenario 2] Adelanto de $200.00 en EFECTIVO_CAJA emitido y descontado de la gaveta de caja.")

    # =========================================================================
    # ESCENARIO 3: Liquidación de comisiones acumuladas
    # =========================================================================
    monto_liquidacion = 500.00
    liq_payload = {
        "usuario_empleado_id": doc_user_id,
        "tipo_pago": "COMISION_TRATAMIENTOS",
        "monto_comisiones": monto_liquidacion,
        "monto_neto_pagado": monto_liquidacion,
        "metodo_pago": "TRANSFERENCIA",
        "referencia_pago": "TRF-NOM-4921",
        "observaciones": "Liquidación parcial de honorarios por comisiones"
    }
    res_liq = client.post("/api/v1/empleados/pagos", json=liq_payload, headers=headers_admin)
    assert res_liq.status_code == 201
    liq_data = res_liq.json()
    liq_id = liq_data["id"]

    # Reconsultar comisiones del doctor: comisiones_ya_liquidadas debe haber sumado $500.00
    res_comision_post = client.get(f"/api/v1/empleados/comisiones-doctor/{doctor_id}", headers=headers_admin).json()
    esperado_pagado_com = com_ya_pagada_ini + monto_liquidacion
    assert abs(res_comision_post["comisiones_ya_liquidadas"] - esperado_pagado_com) < 0.01
    esperado_saldo_com = com_bruta_ini - esperado_pagado_com
    assert abs(res_comision_post["saldo_comision_por_pagar"] - esperado_saldo_com) < 0.01
    print(f"✔ [Escenario 3] Liquidación de $500.00 aplicada. Comisiones liquidadas: ${res_comision_post['comisiones_ya_liquidadas']:.2f}, Nuevo saldo pendiente: ${res_comision_post['saldo_comision_por_pagar']:.2f}.")

    # =========================================================================
    # ESCENARIO 4: Consulta de recibos con aislamiento por empleado
    # =========================================================================
    login_doc_test = client.post("/api/v1/auth/login", data={"username": doc_username, "password": doc_password})
    headers_doc_test = {"Authorization": f"Bearer {login_doc_test.json()['access_token']}"}

    res_doc_pagos = client.get("/api/v1/empleados/pagos", headers=headers_doc_test)
    assert res_doc_pagos.status_code == 200
    pagos_propios = res_doc_pagos.json()
    assert len(pagos_propios) >= 2
    for p in pagos_propios:
        assert p["usuario_empleado_id"] == doc_user_id
    print("✔ [Escenario 4] Aislamiento de privacidad: Doctor solo ve sus propios recibos de nómina.")

    # =========================================================================
    # ESCENARIO 5: Trazabilidad forense en auditoria_logs
    # =========================================================================
    res_audit = client.get("/api/v1/auditoria/?tabla_afectada=pagos_empleados", headers=headers_admin)
    assert res_audit.status_code == 200
    logs_empleados = res_audit.json()
    ids_auditados = [l["registro_id"] for l in logs_empleados]
    assert adelanto_id in ids_auditados
    assert liq_id in ids_auditados
    print("✔ [Escenario 5] Trazabilidad forense de pagos salariales confirmada en auditoria_logs.")

    print("\n==================================================")
    print("TODAS LAS PRUEBAS DE HU-12 PASARON CON ÉXITO")
    print("==================================================")

if __name__ == "__main__":
    test_hu12_completo()
