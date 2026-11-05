import sys
import os
from datetime import date, timedelta
from decimal import Decimal
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_hu09_completo():
    print("==================================================")
    print("EJECUTANDO SUITE DE PRUEBAS AUTOMATIZADAS: HU-09")
    print("Control de Prótesis y Órdenes de Laboratorio")
    print("==================================================")

    # 1. Login como Administrador
    login_admin = client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    assert login_admin.status_code == 200
    token = login_admin.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✔ [Escenario 0] Autenticación completada.")

    # 2. Obtener Paciente y Doctor
    pacientes_res = client.get("/api/v1/pacientes/", headers=headers)
    assert len(pacientes_res.json()) > 0
    paciente_id = pacientes_res.json()[0]["id"]

    doctores_res = client.get("/api/v1/usuarios/doctores/lista", headers=headers)
    assert len(doctores_res.json()) > 0
    doctor_id = doctores_res.json()[0]["id"]
    print(f"✔ [Setup] Paciente: {paciente_id}, Doctor: {doctor_id}")

    # =========================================================================
    # ESCENARIO 1: Envío de orden a laboratorio protésico
    # =========================================================================
    hoy = date.today()
    entrega_esperada = (hoy + timedelta(days=7)).isoformat()
    orden_payload = {
        "paciente_id": paciente_id,
        "doctor_id": doctor_id,
        "laboratorio_nombre": "Laboratorio Dental Arte & Estética",
        "tipo_trabajo": "CORONA_ZIRCONIO",
        "piezas_dentales": "Pieza 16",
        "color_guia_vita": "A2",
        "instrucciones_tecnicas": "Corona de zirconio monolítico estratificada en cara vestibular. Línea de terminación en chamfer subgingival 0.5mm.",
        "costo_laboratorio": 85.00,
        "fecha_envio": hoy.isoformat(),
        "fecha_entrega_esperada": entrega_esperada,
        "observaciones": "Se envían modelos impresos 3D y registro de mordida en silicona"
    }

    res_orden = client.post("/api/v1/protesis/", json=orden_payload, headers=headers)
    assert res_orden.status_code == 201, f"Error creando orden de prótesis: {res_orden.text}"
    orden_data = res_orden.json()
    orden_id = orden_data["id"]
    assert orden_data["estado"] == "ENVIADO"
    assert orden_data["color_guia_vita"] == "A2"
    assert Decimal(str(orden_data["costo_laboratorio"])) == Decimal("85.00")
    print(f"✔ [Escenario 1] Orden de prótesis enviada al laboratorio (ID: {orden_id}, Guía Vita: A2, Costo: $85.00).")

    # =========================================================================
    # ESCENARIO 2: Recepción física del trabajo en recepción de la clínica
    # =========================================================================
    recepcion_payload = {
        "estado": "RECIBIDO_EN_CLINICA",
        "fecha_recepcion_real": hoy.isoformat(),
        "observaciones": "Entregado por el mensajero en caja sellada con factura"
    }
    res_recep = client.put(f"/api/v1/protesis/{orden_id}", json=recepcion_payload, headers=headers)
    assert res_recep.status_code == 200, f"Error actualizando a recibido: {res_recep.text}"
    data_recep = res_recep.json()
    assert data_recep["estado"] == "RECIBIDO_EN_CLINICA"
    assert data_recep["fecha_recepcion_real"] == hoy.isoformat()
    print("✔ [Escenario 2] Prótesis recibida físicamente en clínica. Estado: RECIBIDO_EN_CLINICA.")

    # =========================================================================
    # ESCENARIO 3: Pago al mensajero desde la gaveta de caja (Egreso vinculado)
    # =========================================================================
    # Asegurar que la caja está abierta; si no, abrirla con fondo inicial
    res_caja_abrir = client.post("/api/v1/caja/abrir", json={
        "monto_inicial_fondo": 200.00,
        "observaciones": "Apertura para prueba HU-09"
    }, headers=headers)
    # Si responde 400 es porque ya había una caja abierta, lo cual es normal y válido

    # Registrar el egreso por pago al laboratorio
    egreso_payload = {
        "categoria": "PAGO_LABORATORIO_PROTESIS",
        "monto": 85.00,
        "concepto_motivo": f"Pago a Laboratorio Arte & Estética por Corona Zirconio pieza 16 (Orden {orden_id[:8]})",
        "numero_recibo_comprobante": "REC-LAB-7842"
    }
    res_egreso = client.post("/api/v1/caja/egresos", json=egreso_payload, headers=headers)
    assert res_egreso.status_code == 201, f"Error registrando egreso en caja: {res_egreso.text}"
    egreso_data = res_egreso.json()
    egreso_id = egreso_data["id"]
    print(f"✔ [Escenario 3.1] Egreso de $85.00 registrado en caja (Egreso ID: {egreso_id}).")

    # Asociar el egreso a la orden de prótesis
    res_link = client.put(f"/api/v1/protesis/{orden_id}", json={"egreso_caja_id": egreso_id}, headers=headers)
    assert res_link.status_code == 200
    assert res_link.json()["egreso_caja_id"] == egreso_id
    print("✔ [Escenario 3.2] Egreso de caja vinculado formalmente a la orden de laboratorio.")

    # =========================================================================
    # ESCENARIO 4: Prueba clínica en boca e Instalación definitiva
    # =========================================================================
    # 4.1 Prueba en boca
    client.put(f"/api/v1/protesis/{orden_id}", json={"estado": "PRUEBA_EN_BOCA"}, headers=headers)
    # 4.2 Instalación y cementación final
    res_final = client.put(f"/api/v1/protesis/{orden_id}", json={
        "estado": "INSTALADO_FINALIZADO",
        "observaciones": "Cementado definitivo con RelyX U200. Ajuste oclusal perfecto."
    }, headers=headers)
    assert res_final.status_code == 200
    assert res_final.json()["estado"] == "INSTALADO_FINALIZADO"
    print("✔ [Escenario 4] Ciclo completado: PRUEBA_EN_BOCA -> INSTALADO_FINALIZADO.")

    # =========================================================================
    # ESCENARIO 5: Filtrado de Órdenes y Auditoría
    # =========================================================================
    res_filtro = client.get(f"/api/v1/protesis/?paciente_id={paciente_id}&estado=INSTALADO_FINALIZADO", headers=headers)
    assert res_filtro.status_code == 200
    ordenes_fin = [o["id"] for o in res_filtro.json()]
    assert orden_id in ordenes_fin
    print("✔ [Escenario 5.1] Filtro de órdenes por Paciente y Estado validado.")

    # Auditoría
    res_audit = client.get("/api/v1/auditoria/?tabla_afectada=ordenes_laboratorio_protesis", headers=headers)
    assert res_audit.status_code == 200
    logs_protesis = [l for l in res_audit.json() if l["registro_id"] == orden_id]
    assert len(logs_protesis) >= 2, "Debe haber registros INSERT y UPDATE para la orden de prótesis"
    print("✔ [Escenario 5.2] Auditoría legal verificada en auditoria_logs.")

    print("\n==================================================")
    print("TODAS LAS PRUEBAS DE HU-09 PASARON CON ÉXITO")
    print("==================================================")

if __name__ == "__main__":
    test_hu09_completo()
