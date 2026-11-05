"""Requisitos mínimos de una contraseña."""
LARGO_MINIMO = 8
DEMASIADO_COMUNES = {
    "password1", "password123", "contraseña1", "contrasena1", "contrasena123", "admin123", "admin1234",
    "qwerty123", "abc12345", "abcd1234", "clinica123", "dental123", "usuario123", "doctor123", "12345678a",
}


def validar_contrasena(contrasena: str) -> str:
    if len(contrasena) < LARGO_MINIMO:
        raise ValueError(f"La contraseña debe tener al menos {LARGO_MINIMO} caracteres")
    if len(contrasena.encode("utf-8")) > 72:
        raise ValueError("La contraseña es demasiado larga")
    if not any(c.isalpha() for c in contrasena) or not any(c.isdigit() for c in contrasena):
        raise ValueError("La contraseña debe combinar letras y números")
    if contrasena.lower() in DEMASIADO_COMUNES:
        raise ValueError("Esa contraseña es demasiado común")
    return contrasena
