"""Reglas de datos que comparten varios formularios."""
import re
from typing import Optional

# Numeración FDI: permanentes 11-18, 21-28, 31-38 y 41-48; temporales 51-55, 61-65, 71-75 y 81-85
PIEZAS_FDI = frozenset(
    [c * 10 + d for c in (1, 2, 3, 4) for d in range(1, 9)]
    + [c * 10 + d for c in (5, 6, 7, 8) for d in range(1, 6)]
)


def validar_pieza_fdi(valor: Optional[int]) -> Optional[int]:
    if valor is not None and valor not in PIEZAS_FDI:
        raise ValueError(f"La pieza {valor} no existe en la numeración dental FDI")
    return valor


def validar_url_imagen(valor: Optional[str]) -> Optional[str]:
    """Solo direcciones web o rutas propias: evita guardar enlaces que ejecuten código."""
    if valor is None:
        return valor
    limpio = valor.strip()
    if not re.match(r"^(https?://|/(?!/))", limpio, re.IGNORECASE):
        raise ValueError("La dirección de la imagen debe empezar con http:// o https://")
    return limpio
