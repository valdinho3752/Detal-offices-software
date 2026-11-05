"""Relación entre las citas y los sillones configurables."""
import re


def numero_sillon_de_notas(notas) -> int:
    """El sillón se guarda en las notas de la cita; sin indicación, la agenda la muestra en el Box 1."""
    coincidencia = re.search(r"Box\s*(\d+)", notas or "")
    return int(coincidencia.group(1)) if coincidencia else 1
