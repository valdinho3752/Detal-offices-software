from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.core.produccion import exigir_configuracion_segura, exigir_contrasena_admin_propia
from app.database import SessionLocal

# Importación de Controladores (Rutas MVC)
from app.controllers.auth_controller import router as auth_router
from app.controllers.usuarios_controller import router as usuarios_router
from app.controllers.asistencia_controller import router as asistencia_router
from app.controllers.pacientes_controller import router as pacientes_router
from app.controllers.odontograma_controller import router as odontograma_router
from app.controllers.tratamientos_controller import router as tratamientos_router
from app.controllers.citas_controller import router as citas_router
from app.controllers.visitas_controller import router as visitas_router
from app.controllers.radiografias_controller import router as radiografias_router
from app.controllers.protesis_controller import router as protesis_router
from app.controllers.caja_controller import router as caja_router
from app.controllers.cobros_cita_controller import router as cobros_cita_router
from app.controllers.sillones_controller import router as sillones_router
from app.controllers.configuracion_controller import router as configuracion_router
from app.controllers.empleados_controller import router as empleados_router
from app.controllers.auditoria_controller import router as auditoria_router
from app.controllers.reportes_controller import router as reportes_router

if settings.es_produccion:
    exigir_configuracion_segura(settings)


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    if settings.es_produccion:
        db = SessionLocal()
        try:
            exigir_contrasena_admin_propia(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title="API Clínica Dental Gustavo",
    description="Sistema completo de gestión dental: Pacientes, Citas, Odontograma, Finanzas, Nómina y Seguridad",
    version="1.0.0",
    docs_url=None if settings.es_produccion else "/docs",
    redoc_url=None if settings.es_produccion else "/redoc",
    openapi_url=None if settings.es_produccion else "/openapi.json",
    lifespan=ciclo_de_vida,
)

# Configuración de CORS para el Frontend
if settings.origenes_cors:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origenes_cors,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Registro centralizado de controladores con prefijo /api/v1
api_prefix = "/api/v1"
app.include_router(auth_router, prefix=api_prefix)
app.include_router(usuarios_router, prefix=api_prefix)
app.include_router(asistencia_router, prefix=api_prefix)
app.include_router(pacientes_router, prefix=api_prefix)
app.include_router(odontograma_router, prefix=api_prefix)
app.include_router(tratamientos_router, prefix=api_prefix)
app.include_router(citas_router, prefix=api_prefix)
app.include_router(visitas_router, prefix=api_prefix)
app.include_router(radiografias_router, prefix=api_prefix)
app.include_router(protesis_router, prefix=api_prefix)
app.include_router(caja_router, prefix=api_prefix)
app.include_router(cobros_cita_router, prefix=api_prefix)
app.include_router(sillones_router, prefix=api_prefix)
app.include_router(configuracion_router, prefix=api_prefix)
app.include_router(empleados_router, prefix=api_prefix)
app.include_router(auditoria_router, prefix=api_prefix)
app.include_router(reportes_router, prefix=api_prefix)

@app.get("/", tags=["Estado del Sistema"])
def root():
    return {
        "sistema": "Clínica Dental Gustavo - API",
        "estado": "Operativo y conectado a PostgreSQL",
        "version": "1.0.0",
        "documentacion_swagger": "/docs",
        "modulos_activos": [
            "Autenticación y Fichaje",
            "Usuarios, Roles y Permisos",
            "Pacientes y Ficha Médica",
            "Odontograma (Tooth Chart FDI)",
            "Tratamientos y Planes Secuenciales",
            "Citas y Control de Sillón",
            "Historia Clínica Diaria",
            "Radiografías e Imágenes",
            "Órdenes de Prótesis y Laboratorio",
            "Caja Diaria en Vivo y Pagos",
            "Nómina y Comisiones de Empleados",
            "Auditoría Global (Logs de Cambios y Vistas)"
        ]
    }
