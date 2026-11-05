"""Gráficos de Inteligencia de Negocio, dibujados en el servidor con matplotlib."""
import io
import textwrap
from typing import List, Sequence

# Figure sin pyplot: pyplot guarda estado global y no es seguro entre peticiones simultáneas
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import PathPatch
from matplotlib.path import Path

PX_POR_PULGADA = 100
ALTO_BARRA_PX = 18
RADIO_PX = 4
RESERVA_VALOR_PX = 50  # Espacio fijo para el valor al final de la barra, también en paneles estrechos

TEMAS = {
    "claro": {"barra": "#2a78d6", "tinta": "#0b0b0b", "tinta_secundaria": "#52514e", "base": "#c3c2b7"},
    "oscuro": {"barra": "#3987e5", "tinta": "#f0efec", "tinta_secundaria": "#c3c2b7", "base": "#475569"},
}


def _figura(ancho_pulgadas: float, alto_pulgadas: float) -> Figure:
    figura = Figure(figsize=(ancho_pulgadas, alto_pulgadas))
    FigureCanvasAgg(figura)
    return figura


def _png(figura: Figure) -> bytes:
    salida = io.BytesIO()
    figura.savefig(salida, format="png", dpi=200, transparent=True)
    return salida.getvalue()


def _etiqueta(texto: str, ancho: int = 30, lineas: int = 2) -> str:
    return "\n".join(textwrap.wrap(texto, ancho, max_lines=lineas, placeholder="…"))


def _barra(ax, fila: float, valor: float, color: str, x_max: float, filas: int) -> None:
    """Barra horizontal fina: extremo de datos redondeado y recta en la línea base."""
    if valor <= 0:
        return
    caja = ax.get_position()
    ancho_px = caja.width * ax.figure.get_figwidth() * PX_POR_PULGADA
    alto_px = caja.height * ax.figure.get_figheight() * PX_POR_PULGADA
    px_x = x_max / ancho_px
    px_y = filas / alto_px
    medio = ALTO_BARRA_PX * px_y / 2
    rx = min(RADIO_PX * px_x, valor)
    ry = RADIO_PX * px_y
    puntos = [
        (0, fila - medio),
        (valor - rx, fila - medio),
        (valor, fila - medio),
        (valor, fila - medio + ry),
        (valor, fila + medio - ry),
        (valor, fila + medio),
        (valor - rx, fila + medio),
        (0, fila + medio),
        (0, fila - medio),
    ]
    codigos = [Path.MOVETO, Path.LINETO, Path.CURVE3, Path.CURVE3, Path.LINETO, Path.CURVE3, Path.CURVE3, Path.LINETO, Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(puntos, codigos), facecolor=color, edgecolor="none"))


def _panel_barras(ax, valores: Sequence[float], textos: Sequence[str], tema: dict) -> None:
    filas = len(valores)
    caja = ax.get_position()
    ancho_px = caja.width * ax.figure.get_figwidth() * PX_POR_PULGADA
    x_max = max(max(valores), 1) * ancho_px / (ancho_px - RESERVA_VALOR_PX)
    ax.set_xlim(0, x_max)
    ax.set_ylim(filas - 0.5, -0.5)
    for fila, (valor, texto) in enumerate(zip(valores, textos)):
        _barra(ax, fila, valor, tema["barra"], x_max, filas)
        ax.annotate(
            texto, xy=(valor, fila), xytext=(6, 0), textcoords="offset points",
            va="center", ha="left", fontsize=9.5, color=tema["tinta"],
        )
    ax.set_xticks([])
    ax.set_yticks(range(filas))
    ax.tick_params(axis="y", length=0, labelsize=9.5, labelcolor=tema["tinta"])
    ax.set_facecolor("none")
    for lado in ("top", "right", "bottom"):
        ax.spines[lado].set_visible(False)
    ax.spines["left"].set_color(tema["base"])
    ax.spines["left"].set_linewidth(1)


def _sin_datos(mensaje: str, tema: dict) -> bytes:
    figura = _figura(6.4, 1.6)
    figura.text(0.5, 0.5, mensaje, ha="center", va="center", fontsize=11, color=tema["tinta_secundaria"])
    return _png(figura)


def grafico_tratamientos_demanda(items: List, tema_nombre: str) -> bytes:
    """Ranking horizontal: una sola serie, con el valor al final porque una imagen no tiene tooltip."""
    tema = TEMAS[tema_nombre]
    if not items:
        return _sin_datos("Sin tratamientos completados en este periodo", tema)

    filas = len(items)
    alto = 0.42 * filas + 0.2
    figura = _figura(6.4, alto)
    ax = figura.add_axes([2.35 / 6.4, 0.1 / alto, 3.95 / 6.4, (alto - 0.2) / alto])
    _panel_barras(ax, [i.cantidad_realizada for i in items], [str(i.cantidad_realizada) for i in items], tema)
    ax.set_yticklabels([_etiqueta(i.nombre) for i in items])
    return _png(figura)


def grafico_productividad_doctores(doctores: List, tema_nombre: str) -> bytes:
    """Tres paneles con su propia escala, en lugar de mezclar unidades distintas en un doble eje."""
    tema = TEMAS[tema_nombre]
    doctores = [d for d in doctores if d.total_citas > 0]
    doctores = sorted(doctores, key=lambda d: (-d.citas_finalizadas, d.doctor_nombre))[:10]
    if not doctores:
        return _sin_datos("Sin citas en este periodo", tema)

    filas = len(doctores)
    encabezado = 0.32
    alto = 0.42 * filas + encabezado + 0.1
    ancho = 6.4
    izquierda = 1.5
    separacion = 0.14
    ancho_panel = (ancho - izquierda - 0.1 - 2 * separacion) / 3
    paneles = [
        ("Citas atendidas", [d.citas_finalizadas for d in doctores], [str(d.citas_finalizadas) for d in doctores]),
        ("Minutos por cita", [d.promedio_minutos_por_cita for d in doctores], [f"{d.promedio_minutos_por_cita:g}" for d in doctores]),
        ("Ausentismo", [d.tasa_ausentismo_porcentaje for d in doctores], [f"{d.tasa_ausentismo_porcentaje:g}%" for d in doctores]),
    ]

    figura = _figura(ancho, alto)
    for indice, (titulo, valores, textos) in enumerate(paneles):
        x = izquierda + indice * (ancho_panel + separacion)
        ax = figura.add_axes([x / ancho, 0.1 / alto, ancho_panel / ancho, (alto - encabezado - 0.1) / alto])
        _panel_barras(ax, valores, textos, tema)
        if indice == 0:
            ax.set_yticklabels([_etiqueta(d.doctor_nombre, 18) for d in doctores])
        else:
            ax.set_yticklabels([])
        ax.text(0, 1.0, titulo, transform=ax.transAxes, ha="left", va="bottom", fontsize=9.5, color=tema["tinta_secundaria"], fontweight="semibold")
        ax.title.set_visible(False)
        ax.spines["left"].set_position(("data", 0))
    return _png(figura)
