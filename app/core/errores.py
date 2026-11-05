"""Respuestas claras cuando la base rechaza un dato, en lugar de un error interno."""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import StatementError

registro = logging.getLogger("clinica.errores")

MENSAJES_POSTGRES = {
    "23503": (400, "Uno de los datos relacionados no existe o sigue en uso"),
    "23505": (409, "Ya existe un registro con esos datos"),
    "23502": (422, "Falta un dato obligatorio"),
    "23514": (422, "Uno de los datos no es válido"),
    "22001": (422, "Uno de los textos es demasiado largo"),
    "22003": (422, "Uno de los montos o números es demasiado grande"),
}


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(StatementError)
    async def error_de_base(request: Request, error: StatementError):
        original = error.orig
        codigo = getattr(original, "pgcode", None)
        if codigo in MENSAJES_POSTGRES:
            estado, detalle = MENSAJES_POSTGRES[codigo]
            return JSONResponse(status_code=estado, content={"detail": detalle})
        if isinstance(original, ValueError) and "NUL" in str(original):
            return JSONResponse(status_code=422, content={"detail": "Uno de los textos tiene caracteres no válidos"})
        registro.exception("Error de base de datos en %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Error interno del sistema. Inténtalo de nuevo."})

    @app.exception_handler(Exception)
    async def error_inesperado(request: Request, error: Exception):
        if isinstance(error, ValueError) and "NUL" in str(error):
            return JSONResponse(status_code=422, content={"detail": "Uno de los textos tiene caracteres no válidos"})
        # El detalle queda en los registros del servidor, nunca en la respuesta
        registro.exception("Error inesperado en %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Error interno del sistema. Inténtalo de nuevo."})
