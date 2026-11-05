"""
Frena los intentos de adivinar contraseñas. Se guarda en memoria: basta con un solo proceso del backend,
y reiniciarlo solo borra los bloqueos vigentes.
"""
import threading
import time
from collections import defaultdict
from typing import Optional

from fastapi import HTTPException, status

VENTANA_SEGUNDOS = 15 * 60
MAXIMO_POR_USUARIO = 5  # Por usuario y equipo: nadie puede bloquear a otro desde otra dirección
MAXIMO_POR_EQUIPO = 50  # Frena probar muchos usuarios desde una misma dirección


class LimiteIntentos:
    def __init__(self, reloj=time.monotonic):
        self._reloj = reloj
        self._cerrojo = threading.Lock()
        self._por_usuario = defaultdict(list)
        self._por_equipo = defaultdict(list)

    def _vigentes(self, intentos: dict, clave) -> list:
        limite = self._reloj() - VENTANA_SEGUNDOS
        vigentes = [t for t in intentos[clave] if t > limite]
        if vigentes:
            intentos[clave] = vigentes
        else:
            del intentos[clave]
        return vigentes

    def _espera(self, intentos: list, maximo: int) -> Optional[int]:
        if len(intentos) < maximo:
            return None
        return int(intentos[0] + VENTANA_SEGUNDOS - self._reloj()) + 1

    def exigir_permitido(self, usuario: str, equipo: str) -> None:
        with self._cerrojo:
            espera = self._espera(self._vigentes(self._por_usuario, (usuario.lower(), equipo)), MAXIMO_POR_USUARIO) \
                or self._espera(self._vigentes(self._por_equipo, equipo), MAXIMO_POR_EQUIPO)
        if espera:
            minutos = max(1, round(espera / 60))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Demasiados intentos fallidos. Vuelve a intentarlo en {minutos} minuto(s).",
                headers={"Retry-After": str(espera)},
            )

    def registrar_fallo(self, usuario: str, equipo: str) -> None:
        with self._cerrojo:
            ahora = self._reloj()
            self._por_usuario[(usuario.lower(), equipo)].append(ahora)
            self._por_equipo[equipo].append(ahora)

    def registrar_exito(self, usuario: str, equipo: str) -> None:
        with self._cerrojo:
            self._por_usuario.pop((usuario.lower(), equipo), None)


limite_login = LimiteIntentos()
