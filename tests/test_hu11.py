import sys
import os
from decimal import Decimal
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_hu11_completo():
    print("==================================================")
    print("EJECUTANDO SUITE DE PRUEBAS AUTOMATIZADAS: HU-11")
    print("Cobranzas a Pacientes, Recibos y Saldo Deudor")
    print("==================================================")

    # 1. Login como Administrador
    login_admin = client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    assert login_admin.status_code == 200
    token = login_admin.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✔ [Escenario 0] Autenticación completada.")

    # 2. Obtener Paciente y Doctor (creamos un paciente aislado para garantizar saldo determinista)
    import random
    rand_doc = f"CI-{random.randint(1000000, 9999999)}"
    nuevo_paciente = client.post("/api/v1/pacientes/", json={
        "nombres": "Paciente",
        "apellidos": f"Cobranza {rand_doc}",
        "tipo_documento": "CI",
        "numero_documento": rand_doc,
        "fecha_nacimiento": "1990-01-01",
        "genero": "MASCULINO",
        "telefono": "+591-79911223",
        "email": f"cobranza_{rand_doc}@test.com"
    }, headers=headers).json()
    paciente_id = nuevo_paciente["id"]

    doctores_res = client.get("/api/v1/usuarios/doctores/lista", headers=headers)
    assert len(doctores_res.json()) > 0
    doctor_id = doctores_res.json()[0]["id"]

    # 3. Setup de Caja: Asegurar que hay una caja abierta para recibir los pagos
    estado_caja = client.get("/api/v1/caja/estado", headers=headers).json()
    if not estado_caja.get("caja_abierta"):
        client.post("/api/v1/caja/abrir", json={"monto_inicial_fondo": 100.00, "observaciones": "Caja para HU-11"}, headers=headers)
    estado_caja = client.get("/api/v1/caja/estado", headers=headers).json()
    caja_id = estado_caja["caja_id"]
    gaveta_inicial = estado_caja["efectivo_actual_en_gaveta"]
    print(f"✔ [Setup] Caja activa lista (ID: {caja_id}, Efectivo previo en gaveta: ${gaveta_inicial:.2f})")

    # 4. Crear un Plan de Tratamiento específico para el paciente con valor exacto de $500.00
    cat_res = client.get("/api/v1/tratamientos/catalogo", headers=headers)
    cat_items = cat_res.json()
    cat_id = cat_items[0]["id"]

    nuevo_plan = {
        "paciente_id": paciente_id,
        "doctor_id": doctor_id,
        "titulo": "Plan de Rehabilitación Integral HU-11"
    }
    res_plan = client.post("/api/v1/tratamientos/planes", json=nuevo_plan, headers=headers)
    assert res_plan.status_code == 201
    plan_id = res_plan.json()["id"]

    # Ítem 1: $250.00
    client.post("/api/v1/tratamientos/items", json={
        "plan_id": plan_id,
        "tratamiento_id": cat_id,
        "pieza_fdi": 11,
        "orden_secuencia": 1,
        "costo_acordado": 250.00
    }, headers=headers)

    # Ítem 2: $250.00
    client.post("/api/v1/tratamientos/items", json={
        "plan_id": plan_id,
        "tratamiento_id": cat_id,
        "pieza_fdi": 21,
        "orden_secuencia": 2,
        "costo_acordado": 250.00
    }, headers=headers)

    # Actualizar costo_total = 500.00 y estado = APROBADO
    client.put(f"/api/v1/tratamientos/planes/{plan_id}", json={
        "estado": "APROBADO",
        "costo_total": 500.00
    }, headers=headers)

    # Consultar saldo previo antes de los nuevos pagos
    saldo_previo_data = client.get(f"/api/v1/pacientes/{paciente_id}/saldo", headers=headers).json()
    total_pagado_base = Decimal(str(saldo_previo_data["total_pagado"]))
    total_presup_base = Decimal(str(saldo_previo_data["total_presupuestado"]))
    print(f"✔ [Setup] Plan creado y APROBADO por $500.00. Presupuesto total acumulado del paciente: ${total_presup_base:.2f}")

    # =========================================================================
    # ESCENARIO 1: Registro de cobro en efectivo y actualización de caja
    # =========================================================================
    pago_efectivo_payload = {
        "paciente_id": paciente_id,
        "plan_id": plan_id,
        "doctor_comision_id": doctor_id,
        "monto": 150.00,
        "metodo_pago": "EFECTIVO",
        "referencia_comprobante": "REC-EF-101",
        "observaciones": "Abono inicial en efectivo por inicio de carillas"
    }
    res_p1 = client.post("/api/v1/caja/pagos", json=pago_efectivo_payload, headers=headers)
    assert res_p1.status_code == 201, f"Error registrando pago en efectivo: {res_p1.text}"
    p1_data = res_p1.json()
    p1_id = p1_data["id"]
    assert p1_data["caja_sesion_id"] == caja_id
    assert p1_data["metodo_pago"] == "EFECTIVO"
    assert Decimal(str(p1_data["monto"])) == Decimal("150.00")

    # Verificar que el efectivo en gaveta aumentó exactamente en $150.00
    estado_caja_post1 = client.get("/api/v1/caja/estado", headers=headers).json()
    esperado_gaveta1 = float(Decimal(str(gaveta_inicial)) + Decimal("150.00"))
    assert abs(estado_caja_post1["efectivo_actual_en_gaveta"] - esperado_gaveta1) < 0.01
    print(f"✔ [Escenario 1] Cobro en efectivo por $150.00 insertado en caja activa. Efectivo en gaveta: ${estado_caja_post1['efectivo_actual_en_gaveta']:.2f}")

    # =========================================================================
    # ESCENARIO 2: Registro de cobro bancario (Transferencia)
    # =========================================================================
    pago_transf_payload = {
        "paciente_id": paciente_id,
        "plan_id": plan_id,
        "doctor_comision_id": doctor_id,
        "monto": 200.00,
        "metodo_pago": "TRANSFERENCIA",
        "referencia_comprobante": "TRANSF-BNB-998811",
        "observaciones": "Pago por transferencia bancaria BNB"
    }
    res_p2 = client.post("/api/v1/caja/pagos", json=pago_transf_payload, headers=headers)
    assert res_p2.status_code == 201
    p2_data = res_p2.json()
    p2_id = p2_data["id"]

    # Verificar que la gaveta de efectivo físico NO cambió, pero sí la recaudación de transferencias
    estado_caja_post2 = client.get("/api/v1/caja/estado", headers=headers).json()
    assert abs(estado_caja_post2["efectivo_actual_en_gaveta"] - esperado_gaveta1) < 0.01
    assert estado_caja_post2["ingresos_otros_medios"]["transferencia"] >= 200.00
    print(f"✔ [Escenario 2] Cobro por Transferencia ($200.00) registrado sin alterar los billetes de gaveta física.")

    # =========================================================================
    # ESCENARIO 3: Actualización instantánea del saldo deudor del paciente
    # =========================================================================
    res_saldo = client.get(f"/api/v1/pacientes/{paciente_id}/saldo", headers=headers)
    assert res_saldo.status_code == 200
    saldo_info = res_saldo.json()
    # Debe reflejar los nuevos $350.00 pagados ($150 + $200)
    esperado_pagado = float(total_pagado_base + Decimal("350.00"))
    assert abs(saldo_info["total_pagado"] - esperado_pagado) < 0.01
    esperado_pendiente = float(total_presup_base - Decimal(str(esperado_pagado)))
    assert abs(saldo_info["saldo_pendiente"] - esperado_pendiente) < 0.01
    assert saldo_info["estado_saldo"] == ("DEUDOR" if esperado_pendiente > 0 else "AL_DIA")
    print(f"✔ [Escenario 3] Saldo en vivo del paciente verificado: Presupuestado: ${saldo_info['total_presupuestado']:.2f}, Pagado: ${saldo_info['total_pagado']:.2f}, Pendiente: ${saldo_info['saldo_pendiente']:.2f} ({saldo_info['estado_saldo']}).")

    # =========================================================================
    # ESCENARIO 4: Pago final para liquidación de saldo
    # =========================================================================
    pago_final_payload = {
        "paciente_id": paciente_id,
        "plan_id": plan_id,
        "monto": esperado_pendiente,
        "metodo_pago": "EFECTIVO",
        "referencia_comprobante": "REC-LIQ-TOTAL",
        "observaciones": "Liquidación total de saldo pendiente"
    }
    res_p3 = client.post("/api/v1/caja/pagos", json=pago_final_payload, headers=headers)
    assert res_p3.status_code == 201

    res_saldo_final = client.get(f"/api/v1/pacientes/{paciente_id}/saldo", headers=headers)
    assert res_saldo_final.status_code == 200
    saldo_fin = res_saldo_final.json()
    assert abs(saldo_fin["saldo_pendiente"]) < 0.01
    assert saldo_fin["estado_saldo"] == "AL_DIA"
    print(f"✔ [Escenario 4] Liquidación total completada: Saldo pendiente: $0.00, Estado: AL_DIA.")

    # =========================================================================
    # ESCENARIO 5: Auditoría forense de los cobros
    # =========================================================================
    res_audit = client.get("/api/v1/auditoria/?tabla_afectada=pagos", headers=headers)
    assert res_audit.status_code == 200
    logs_pagos = res_audit.json()
    ids_auditados = [l["registro_id"] for l in logs_pagos]
    assert p1_id in ids_auditados
    assert p2_id in ids_auditados
    print("✔ [Escenario 5] Trazabilidad forense de cobros confirmada en auditoria_logs.")

    print("\n==================================================")
    print("TODAS LAS PRUEBAS DE HU-11 PASARON CON ÉXITO")
    print("==================================================")

if __name__ == "__main__":
    test_hu11_completo()
