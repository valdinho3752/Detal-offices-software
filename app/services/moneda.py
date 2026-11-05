"""Cómo se escribe un monto: el mismo formato que usa la pantalla."""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import ConfiguracionClinica

SIMBOLO_POR_DEFECTO = "$"


def obtener_configuracion(db: Session) -> ConfiguracionClinica:
    configuracion = db.get(ConfiguracionClinica, 1)
    if not configuracion:
        configuracion = ConfiguracionClinica(id=1, moneda_simbolo=SIMBOLO_POR_DEFECTO)
        db.add(configuracion)
        db.flush()
    return configuracion


def texto_moneda(monto, db: Session) -> str:
    """Ejemplos: $1.500,00 · Bs. 1.500,00 · -S/ 20,00"""
    simbolo = obtener_configuracion(db).moneda_simbolo
    valor = Decimal(monto)
    numero = f"{abs(valor):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    separador = " " if len(simbolo) > 1 else ""
    return f"{'-' if valor < 0 else ''}{simbolo}{separador}{numero}"
