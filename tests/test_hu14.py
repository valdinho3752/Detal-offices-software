import sys
import os
from decimal import Decimal
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_hu14_completo():
    print("==================================================")
    print("EJECUTANDO SUITE DE PRUEBAS AUTOMATIZADAS: HU-14")
    print("Reportes de Productividad Médica, Rentabilidad y BI")
    print("==================================================")

    # 1. Login como Administrador
    login_admin = client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    assert login_admin.status_code == 200
    token_admin = login_admin.json()["access_token"]
    headers_admin = {"Authorization": f"Bearer {token_admin}"}
    print("✔ [Escenario 0] Admin autenticado con éxito.")

    # 2. Control RBAC: Empleado no-admin es bloqueado con 403 Forbidden
    login_asist = client.post("/api/v1/auth/login", data={"username": "asist_hu06_fichaje", "password": "AsistPassword123"})
    if login_asist.status_code == 200:
        headers_asist = {"Authorization": f"Bearer {login_asist.json()['access_token']}"}
        res_block1 = client.get("/api/v1/reportes/tratamientos-demanda", headers=headers_asist)
        assert res_block1.status_code == 403
        res_block2 = client.get("/api/v1/reportes/productividad-doctores", headers=headers_asist)
        assert res_block2.status_code == 403
        print("✔ [Escenario 0.1] Seguridad RBAC: Acceso a reportes analíticos restringido a ADMIN (HTTP 403).")

    # =========================================================================
    # ESCENARIO 1: Reporte de tratamientos con mayor demanda
    # =========================================================================
    res_demanda = client.get("/api/v1/reportes/tratamientos-demanda", headers=headers_admin)
    assert res_demanda.status_code == 200, f"Error en reporte demanda: {res_demanda.text}"
    data_demanda = res_demanda.json()
    assert "total_procedimientos_completados" in data_demanda
    assert "ranking_tratamientos" in data_demanda
    assert isinstance(data_demanda["ranking_tratamientos"], list)

    ranking = data_demanda["ranking_tratamientos"]
    assert len(ranking) > 0, "Debe existir al menos un procedimiento completado en los planes"
    top1 = ranking[0]
    assert "codigo" in top1
    assert "nombre" in top1
    assert "categoria" in top1
    assert top1["cantidad_realizada"] >= 1
    assert Decimal(str(top1["facturacion_total"])) > 0
    print(f"✔ [Escenario 1] Ranking de tratamientos obtenido: Top 1: '{top1['nombre']}' ({top1['categoria']}) con {top1['cantidad_realizada']} sesiones ejecutadas y ${float(top1['facturacion_total']):.2f} facturados.")

    # =========================================================================
    # ESCENARIO 2: Métrica de ocupación y tiempo en sillón dental
    # =========================================================================
    res_prod = client.get("/api/v1/reportes/productividad-doctores", headers=headers_admin)
    assert res_prod.status_code == 200, f"Error en productividad: {res_prod.text}"
    data_prod = res_prod.json()
    assert "resumen_global_citas" in data_prod
    assert "doctores" in data_prod
    assert data_prod["resumen_global_citas"] > 0

    doctores = data_prod["doctores"]
    assert len(doctores) > 0

    # Buscar doctor con citas en sillón
    doc_activo = next((d for d in doctores if d["tiempo_total_sillon_minutos"] > 0), None)
    assert doc_activo is not None, "Debe existir al menos un doctor con tiempo en sillón registrado (HU-05)"
    assert doc_activo["citas_finalizadas"] >= 1
    assert doc_activo["tiempo_total_sillon_minutos"] >= 45  # Los 45 min calculados por trigger en HU-05
    assert doc_activo["promedio_minutos_por_cita"] >= 45.0
    print(f"✔ [Escenario 2] Productividad en sillón verificada: Dr. {doc_activo['doctor_nombre']} acumuló {doc_activo['tiempo_total_sillon_minutos']} minutos de sillón efectivo en {doc_activo['citas_finalizadas']} citas finalizadas (Promedio: {doc_activo['promedio_minutos_por_cita']} min/cita).")

    # Filtro específico por doctor_id
    doc_id_target = doc_activo["doctor_id"]
    res_filtro_doc = client.get(f"/api/v1/reportes/productividad-doctores?doctor_id={doc_id_target}", headers=headers_admin)
    assert res_filtro_doc.status_code == 200
    docs_filtrados = res_filtro_doc.json()["doctores"]
    assert len(docs_filtrados) == 1
    assert docs_filtrados[0]["doctor_id"] == doc_id_target
    print(f"✔ [Escenario 2.1] Filtro analítico por doctor_id específico validado.")

    # =========================================================================
    # ESCENARIO 3: Balance Financiero Global y Rentabilidad Operativa
    # =========================================================================
    res_fin = client.get("/api/v1/reportes/resumen-financiero", headers=headers_admin)
    assert res_fin.status_code == 200, f"Error en resumen financiero: {res_fin.text}"
    fin = res_fin.json()

    total_ingresos = Decimal(str(fin["total_ingresos"]))
    total_egresos = Decimal(str(fin["total_egresos"]))
    balance_neto = Decimal(str(fin["balance_neto_operativo"]))

    assert total_ingresos > 0, "Debe registrar ingresos cobrados en pruebas previas"
    assert total_egresos > 0, "Debe registrar egresos en caja de pruebas previas"
    assert balance_neto == (total_ingresos - total_egresos)

    # Verificar que los métodos de pago tienen sus subtotales
    assert "EFECTIVO" in fin["ingresos_por_metodo"]
    assert "TRANSFERENCIA" in fin["ingresos_por_metodo"]
    assert Decimal(str(fin["ingresos_por_metodo"]["EFECTIVO"])) > 0
    assert Decimal(str(fin["ingresos_por_metodo"]["TRANSFERENCIA"])) > 0

    print(f"✔ [Escenario 3] Balance Financiero Global consolidado:")
    print(f"     Total Ingresos Cobrados : ${float(total_ingresos):.2f}")
    print(f"     Total Egresos Operativos: ${float(total_egresos):.2f}")
    print(f"     Margen Operativo Neto   : ${float(balance_neto):.2f}")

    print("\n==================================================")
    print("TODAS LAS PRUEBAS DE HU-14 PASARON CON ÉXITO")
    print("==================================================")

if __name__ == "__main__":
    test_hu14_completo()
