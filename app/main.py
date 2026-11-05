from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

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
from app.controllers.empleados_controller import router as empleados_router
from app.controllers.auditoria_controller import router as auditoria_router
from app.controllers.reportes_controller import router as reportes_router

app = FastAPI(
    title="API Clínica Dental Gustavo",
    description="Sistema completo de gestión dental: Pacientes, Citas, Odontograma, Finanzas, Nómina y Seguridad",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuración de CORS para el Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
