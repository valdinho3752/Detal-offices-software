import sys
import os
from decimal import Decimal
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_hu10_completo():
    print("==================================================")
    print("EJECUTANDO SUITE DE PRUEBAS AUTOMATIZADAS: HU-10")
    print("Apertura, Cierre y Arqueo de Caja Operativa")
    print("==================================================")

    # 1. Login como Administrador
    login_admin = client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    assert login_admin.status_code == 200
    token = login_admin.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✔ [Escenario 0] Autenticación completada.")

    # 2. Obtener Paciente para los pagos
    pacientes_res = client.get("/api/v1/pacientes/", headers=headers)
    assert len(pacientes_res.json()) > 0
    paciente_id = pacientes_res.json()[0]["id"]

    # 3. Limpieza previa: si hay una caja abierta de ejecuciones anteriores, la cerramos
    estado_ini = client.get("/api/v1/caja/estado", headers=headers).json()
    if estado_ini.get("caja_abierta"):
        saldo_previo = estado_ini.get("efectivo_actual_en_gaveta", 0.0)
        client.post("/api/v1/caja/cerrar", json={"total_efectivo_contado": saldo_previo, "observaciones": "Cierre previo de limpieza"}, headers=headers)
        print("✔ [Setup] Caja previa cerrada para iniciar prueba limpia.")

    # =========================================================================
    # ESCENARIO 1: Apertura de turno con fondo inicial
    # =========================================================================
    apertura_payload = {
        "monto_inicial_fondo": 150.00,
        "observaciones": "Apertura de turno mañana con $150 de cambio"
    }
    res_apertura = client.post("/api/v1/caja/abrir", json=apertura_payload, headers=headers)
    assert res_apertura.status_code == 201, f"Error abriendo caja: {res_apertura.text}"
    caja_data = res_apertura.json()
    caja_id = caja_data["id"]
    assert caja_data["estado"] == "ABIERTA"
    assert Decimal(str(caja_data["monto_inicial_fondo"])) == Decimal("150.00")
    assert Decimal(str(caja_data["saldo_efectivo_esperado"])) == Decimal("150.00")
    print(f"✔ [Escenario 1.1] Turno de caja abierto (ID: {caja_id}, Fondo Inicial: $150.00, Estado: ABIERTA).")

    # Rechazo de segunda caja concurrente
    res_doble = client.post("/api/v1/caja/abrir", json={"monto_inicial_fondo": 50.00}, headers=headers)
    assert res_doble.status_code == 400, "Debe rechazar abrir dos cajas simultáneamente"
    print("✔ [Escenario 1.2] Rechazo de apertura concurrente de caja validado (HTTP 400).")

    # =========================================================================
    # ESCENARIO 2: Movimientos de ingresos y egresos y Monitoreo en Tiempo Real
    # =========================================================================
    # 2.1 Pago de paciente en efectivo: $200.00
    pago_efectivo = {
        "paciente_id": paciente_id,
        "monto": 200.00,
        "metodo_pago": "EFECTIVO",
        "referencia_comprobante": "REC-001-EF",
        "observaciones": "Pago en efectivo por consulta y radiografía"
    }
    res_pago1 = client.post("/api/v1/caja/pagos", json=pago_efectivo, headers=headers)
    assert res_pago1.status_code == 201
    print("✔ [Escenario 2.1] Ingreso de efectivo registrado: +$200.00.")

    # 2.2 Pago de paciente con tarjeta de débito: $100.00 (no afecta la gaveta física de billetes)
    pago_tarjeta = {
        "paciente_id": paciente_id,
        "monto": 100.00,
        "metodo_pago": "TARJETA_DEBITO",
        "referencia_comprobante": "VOUCHER-POS-893",
        "observaciones": "Pago con tarjeta de débito"
    }
    res_pago2 = client.post("/api/v1/caja/pagos", json=pago_tarjeta, headers=headers)
    assert res_pago2.status_code == 201
    print("✔ [Escenario 2.2] Ingreso por tarjeta registrado: +$100.00 (sin sumar a gaveta física).")

    # 2.3 Egreso de caja por compra urgente de insumos: -$30.00
    egreso_insumos = {
        "categoria": "COMPRA_INSUMOS",
        "monto": 30.00,
        "concepto_motivo": "Compra urgente de guantes de látex y papel toalla",
        "numero_recibo_comprobante": "FACT-FARM-445"
    }
    res_egreso = client.post("/api/v1/caja/egresos", json=egreso_insumos, headers=headers)
    assert res_egreso.status_code == 201
    print("✔ [Escenario 2.3] Egreso de efectivo registrado: -$30.00.")

    # 2.4 Consulta en tiempo real del estado de caja (GET /api/v1/caja/estado)
    # Fondo ($150) + Efectivo ($200) - Egreso ($30) = $320.00 esperado en gaveta
    res_estado = client.get("/api/v1/caja/estado", headers=headers)
    assert res_estado.status_code == 200
    estado = res_estado.json()
    assert estado["caja_abierta"] is True
    assert estado["fondo_inicial"] == 150.00
    assert estado["total_cobrado_efectivo"] == 200.00
    assert estado["total_egresos_efectivo"] == 30.00
    assert estado["efectivo_actual_en_gaveta"] == 320.00
    assert estado["ingresos_otros_medios"]["tarjeta_debito"] == 100.00
    assert estado["total_recaudacion_global_sesion"] == 300.00  # 200 ef + 100 deb
    print(f"✔ [Escenario 2.4] Arqueo en vivo verificado con precisión: Fondo $150 + Ingresos $200 - Egresos $30 = ${estado['efectivo_actual_en_gaveta']:.2f} en gaveta.")

    # =========================================================================
    # ESCENARIO 3: Cierre de caja y detección de descuadre
    # =========================================================================
    # El cajero cuenta el dinero físico y encuentra $315.00 (faltante de -$5.00 respecto a $320.00 esperados)
    cierre_payload = {
        "total_efectivo_contado": 315.00,
        "observaciones": "Faltante de $5.00 por diferencia de cambio en gaveta."
    }
    res_cierre = client.post("/api/v1/caja/cerrar", json=cierre_payload, headers=headers)
    assert res_cierre.status_code == 200, f"Error al cerrar caja: {res_cierre.text}"
    caja_cerrada = res_cierre.json()
    assert caja_cerrada["estado"] == "CERRADA"
    assert Decimal(str(caja_cerrada["saldo_efectivo_esperado"])) == Decimal("320.00")
    assert Decimal(str(caja_cerrada["total_efectivo_contado"])) == Decimal("315.00")
    assert Decimal(str(caja_cerrada["diferencia_descuadre"])) == Decimal("-5.00")
    assert caja_cerrada["fecha_cierre"] is not None
    assert caja_cerrada["usuario_cierre_id"] is not None
    print(f"✔ [Escenario 3] Caja CERRADA con éxito. Saldo Esperado: $320.00, Contado: $315.00, Descuadre detectado: -$5.00.")

    # =========================================================================
    # ESCENARIO 4: Validación de caja cerrada y Auditoría
    # =========================================================================
    # 4.1 Intentar registrar un egreso cuando la caja ya está cerrada
    res_egreso_fail = client.post("/api/v1/caja/egresos", json=egreso_insumos, headers=headers)
    assert res_egreso_fail.status_code == 400
    print("✔ [Escenario 4.1] Bloqueo de egreso sin caja abierta verificado (HTTP 400).")

    # 4.2 Estado de caja debe reportar cerrada
    res_estado_post = client.get("/api/v1/caja/estado", headers=headers)
    assert res_estado_post.status_code == 200
    assert res_estado_post.json()["caja_abierta"] is False
    print("✔ [Escenario 4.2] /api/v1/caja/estado reporta caja_abierta: false.")

    # 4.3 Auditoría
    res_audit = client.get("/api/v1/auditoria/?tabla_afectada=cajas_sesiones", headers=headers)
    assert res_audit.status_code == 200
    logs_caja = [l for l in res_audit.json() if l["registro_id"] == caja_id]
    assert len(logs_caja) >= 2, "Debe existir log INSERT (apertura) y UPDATE (cierre)"
    print("✔ [Escenario 4.3] Trazabilidad forense verificada en auditoria_logs.")

    print("\n==================================================")
    print("TODAS LAS PRUEBAS DE HU-10 PASARON CON ÉXITO")
    print("==================================================")

if __name__ == "__main__":
    test_hu10_completo()
