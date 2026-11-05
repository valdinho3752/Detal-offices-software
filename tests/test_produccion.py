"""
Arranque seguro, base limpia, migraciones y copias de seguridad.
Crea y elimina sus propias bases temporales; no modifica la base configurada.
"""
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from uuid import uuid4

RAIZ = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(RAIZ), str(RAIZ / "scripts"), str(RAIZ / "database")]

import comun
import crear_base_limpia
import migrar
import respaldar
import restaurar
from app.core.produccion import CLAVE_JWT_PUBLICADA, problemas_de_configuracion

CLAVE = "x" * 48
CONTRASENA = "Clave-De-Prueba-2026!"


def _config(**cambios):
    base = dict(
        DEBUG=False, SECRET_KEY=CLAVE, DATABASE_URL="postgresql+psycopg2://u:ClaveLarga99@h/db",
        CLINICA_TIMEZONE="America/La_Paz", origenes_cors=[],
    )
    return SimpleNamespace(**{**base, **cambios})


def _proceso(codigo, **entorno):
    return subprocess.run(
        [sys.executable, "-c", codigo], cwd=RAIZ, env={**os.environ, "PYTHONIOENCODING": "utf-8", **entorno},
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def _eliminar(base):
    assert base.startswith("clinica_tmp_test_")
    comun.ejecutar_sin_transaccion(f'DROP DATABASE IF EXISTS "{base}" WITH (FORCE)')


def _consulta(base, sql):
    conexion = comun.conectar(base)
    try:
        with conexion.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()
    finally:
        conexion.close()


def test_configuracion_de_produccion():
    assert problemas_de_configuracion(_config()) == []
    casos = {
        "DEBUG": {"DEBUG": True},
        "SECRET_KEY": {"SECRET_KEY": ""},
        "contraseña": {"DATABASE_URL": "postgresql+psycopg2://u:1234@h/db"},
        "CLINICA_TIMEZONE": {"CLINICA_TIMEZONE": " "},
        "CORS_ORIGINS": {"origenes_cors": ["*"]},
    }
    for texto, cambio in casos.items():
        assert any(texto in p for p in problemas_de_configuracion(_config(**cambio))), texto
    assert problemas_de_configuracion(_config(SECRET_KEY=CLAVE_JWT_PUBLICADA)), "La clave publicada no sirve"
    assert problemas_de_configuracion(_config(SECRET_KEY="corta")), "Una clave corta no sirve"
    print("✔ Producción: la configuración insegura se detecta.")


def test_no_arranca_con_configuracion_insegura():
    res = _proceso("import app.main", ENV="production", DEBUG="True", SECRET_KEY="corta")
    assert res.returncode != 0 and "No se puede arrancar en producción" in res.stderr
    print("✔ Producción: no arranca con configuración insegura.")


def test_base_limpia_y_arranque():
    base = f"clinica_tmp_test_{uuid4().hex[:10]}"
    try:
        crear_base_limpia.crear(base, CONTRASENA)
        try:
            crear_base_limpia.crear(base, CONTRASENA)
            raise AssertionError("No debe aceptar una base existente")
        except SystemExit as error:
            assert "ya existe" in str(error)

        for tabla in ("pacientes", "citas", "pagos", "catalogo_tratamientos", "cajas_sesiones"):
            assert _consulta(base, f"select count(*) from {tabla}")[0][0] == 0, tabla
        assert [f[0] for f in _consulta(base, "select username from usuarios")] == ["admin"]
        assert _consulta(base, "select count(*) from sillones where activo")[0][0] == 3
        assert _consulta(base, "select count(*) from permisos where codigo_permiso = 'CAJA_ANULAR_PAGOS'")[0][0] == 1

        # Todas las migraciones quedan registradas: la siguiente actualización no las repite
        registradas = {f[0] for f in _consulta(base, "select nombre from migraciones_aplicadas")}
        assert registradas == {a.name for a in migrar.archivos_migracion()}

        url = comun.url.set(database=base).render_as_string(hide_password=False)
        arranque = """
import sys
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as c:
    assert c.get('/docs').status_code == 404 and c.get('/openapi.json').status_code == 404
    assert c.post('/api/v1/auth/login', data={'username': 'admin', 'password': 'admin123'}).status_code == 401
    r = c.post('/api/v1/auth/login', data={'username': 'admin', 'password': sys.argv[1]})
    assert r.status_code == 200, r.text
    h = {'Authorization': 'Bearer ' + r.json()['access_token']}
    assert c.get('/api/v1/caja/estado', headers=h).status_code == 200
    print('ARRANQUE_OK')
"""
        prod = dict(ENV="production", DEBUG="False", SECRET_KEY=CLAVE, DATABASE_URL=url, CLINICA_TIMEZONE="America/La_Paz", CORS_ORIGINS="")
        res = subprocess.run(
            [sys.executable, "-c", arranque, CONTRASENA], cwd=RAIZ, env={**os.environ, "PYTHONIOENCODING": "utf-8", **prod},
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        # Sin una contraseña de base segura también debe detenerse: aquí se usa la real solo si es segura
        if comun.url.password in ("1234", "postgres", "admin", "password", "", None):
            assert res.returncode != 0 and "PostgreSQL es insegura" in res.stderr, res.stderr[-400:]
            print("✔ Base limpia: creada; el arranque se detuvo por la contraseña de PostgreSQL de este equipo.")
        else:
            assert "ARRANQUE_OK" in res.stdout, res.stderr[-600:]
            print("✔ Base limpia: creada y arranca en producción.")

        # La contraseña de demostración impide arrancar
        sql_hash = _proceso(
            "from app.core.security import hash_password; print(hash_password('admin123'))"
        ).stdout.strip().splitlines()[-1]
        conexion = comun.conectar(base)
        with conexion.cursor() as cursor:
            cursor.execute("update usuarios set password_hash = %s where username = 'admin'", (sql_hash,))
        conexion.commit()
        conexion.close()
        res = _proceso(
            """
from app.core.produccion import exigir_contrasena_admin_propia
from app.database import SessionLocal
db = SessionLocal()
try:
    exigir_contrasena_admin_propia(db)
except RuntimeError as e:
    print('RECHAZADO', e)
""", DATABASE_URL=url,
        )
        assert "RECHAZADO" in res.stdout, res.stdout + res.stderr[-300:]
        print("✔ Base limpia: la contraseña de demostración impide arrancar.")
    finally:
        _eliminar(base)


def test_migraciones():
    base = f"clinica_tmp_test_{uuid4().hex[:10]}"
    prueba = migrar.CARPETA / f"999_prueba_{uuid4().hex[:6]}.sql"
    try:
        crear_base_limpia.crear(base, CONTRASENA)
        conexion = comun.conectar(base)
        assert migrar.aplicar_pendientes(conexion) == [], "Una base recién creada ya está al día"

        prueba.write_text("CREATE TABLE tabla_migrada (id INT); INSERT INTO tabla_migrada VALUES (1);", encoding="utf-8")
        assert migrar.aplicar_pendientes(conexion) == [prueba.name]
        assert migrar.aplicar_pendientes(conexion) == [], "No se repite"
        assert _consulta(base, "select count(*) from tabla_migrada")[0][0] == 1

        # Una migración con error no deja nada a medias ni queda registrada
        prueba.unlink()
        prueba = migrar.CARPETA / f"999_prueba_{uuid4().hex[:6]}.sql"
        prueba.write_text("CREATE TABLE tabla_parcial (id INT); SELECT columna_inexistente;", encoding="utf-8")
        try:
            migrar.aplicar_pendientes(conexion)
            raise AssertionError("Debe informar el error")
        except SystemExit as error:
            assert prueba.name in str(error)
        assert _consulta(base, "select to_regclass('tabla_parcial')")[0][0] is None
        assert _consulta(base, f"select count(*) from migraciones_aplicadas where nombre = '{prueba.name}'")[0][0] == 0
        conexion.close()
        print("✔ Migraciones: se aplican una vez, y una con error no deja nada a medias.")
    finally:
        prueba.unlink(missing_ok=True)
        _eliminar(base)


def test_respaldo_y_restauracion():
    origen = comun.url.database
    copia = f"clinica_tmp_test_{uuid4().hex[:10]}"
    with TemporaryDirectory() as carpeta:
        try:
            archivo = respaldar.respaldar(Path(carpeta), conservar=30)
            assert archivo.stat().st_size > 0 and not list(Path(carpeta).glob("*.parcial"))
            assert restaurar.restaurar(archivo, copia) == restaurar.contar_filas(origen)

            try:
                restaurar.restaurar(archivo, copia)
                raise AssertionError("No debe sobrescribir una base existente")
            except SystemExit as error:
                assert "nunca sobrescribe" in str(error)
            try:
                restaurar.restaurar(archivo, origen)
                raise AssertionError("No debe sobrescribir la base en uso")
            except SystemExit as error:
                assert "nunca sobrescribe" in str(error)

            # Un archivo dañado no crea una base a medias
            dañado = Path(carpeta) / "clinica_dañado.dump"
            dañado.write_bytes(b"no es una copia")
            otra = f"clinica_tmp_test_{uuid4().hex[:10]}"
            try:
                restaurar.restaurar(dañado, otra)
                raise AssertionError("Debe rechazar un archivo dañado")
            except SystemExit:
                pass
            assert not comun.base_existe(otra)
            dañado.unlink()

            # Solo elimina las copias más antiguas y nada más de la carpeta
            otro_archivo = Path(carpeta) / "notas.txt"
            otro_archivo.write_text("conservar", encoding="utf-8")
            for indice in range(3):
                vieja = Path(carpeta) / f"clinica_vieja_{indice}.dump"
                vieja.write_bytes(b"x")
                os.utime(vieja, (1000 + indice, 1000 + indice))
            respaldar.respaldar(Path(carpeta), conservar=2)
            assert len(list(Path(carpeta).glob("clinica_*.dump"))) == 2 and otro_archivo.exists()
            assert not (Path(carpeta) / "clinica_vieja_2.dump").exists()
            print("✔ Copias: se crean, se restauran con las mismas filas y nunca sobrescriben.")
        finally:
            _eliminar(copia)


def test_nombres_de_base_validados():
    for nombre in ('a"; DROP DATABASE x; --', "Con Espacios", ""):
        try:
            comun.validar_nombre_base(nombre)
            raise AssertionError(nombre)
        except SystemExit:
            pass
    print("✔ Scripts: los nombres de base se validan.")


if __name__ == "__main__":
    test_configuracion_de_produccion()
    test_no_arranca_con_configuracion_insegura()
    test_nombres_de_base_validados()
    test_base_limpia_y_arranque()
    test_migraciones()
    test_respaldo_y_restauracion()
    print("TODAS LAS PRUEBAS PASARON")
