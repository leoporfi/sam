#!/usr/bin/env python3
"""
Script de validación de convención de nombres para variables de entorno.

Convención: {SERVICIO}_{TEMA}_{ACCION}[_{UNIDAD}]

Este script verifica que las nuevas variables en .env.example sigan la convención.
Se ejecuta como parte del pre-commit hook.

Uso:
    python scripts/check_env_naming.py
    python scripts/check_env_naming.py --strict  # Falla en cualquier violación
"""

import re
import sys
from pathlib import Path

# Servicios válidos (prefijos)
VALID_SERVICES = {
    "LOG",
    "SQL_SAM",
    "SQL_RPA360",
    "AA",
    "CALLBACK",
    "EMAIL",
    "LANZADOR",
    "BALANCEADOR",
    "INTERFAZ_WEB",
    "CLOUDERS",
    "APIGW",
    "AUTH",
    "JWT",
    "ROBOTS",
    "API_GATEWAY",  # Deprecated, pero soportado para fallback
}

# Temas conocidos por servicio (para sugerencias)
KNOWN_THEMES = {
    "LANZADOR": ["SYNC", "CONCILIACION", "DEPLOY", "ROBOT", "CICLO", "PAUSA", "ALERTAS", "WORKERS"],
    "BALANCEADOR": ["POOL", "CICLO", "CARGA", "TICKETS", "PREEMPTION"],
    "INTERFAZ_WEB": ["SESION", "EJECUCION", "UPLOAD", "AA"],
    "SQL_SAM": ["CONEXION", "QUERY", "POOL"],
    "SQL_RPA360": ["CONEXION", "QUERY", "POOL"],
    "AA": ["API", "SSL", "PAGINACION", "TOKEN", "CALLBACK"],
    "CALLBACK": ["AUTH", "HOST", "ENDPOINT"],
    "EMAIL": ["SMTP", "TLS"],
}

# Unidades válidas (sufijos)
VALID_UNITS = {"SEG", "MIN", "MB", "HHMM", "JSON", "MAX"}

# Variables que están exentas (legacy, credenciales, infraestructura básica, etc.)
EXEMPT_PATTERNS = [
    r".*_PASSWORD$",
    r".*_PWD$",
    r".*_TOKEN$",
    r".*_SECRET$",
    r".*_KEY$",
    r".*_APIKEY$",
    r".*_AUTH$",
    r".*_URL$",
    r".*_HOST$",
    r".*_DRIVER$",
    r".*_DEBUG$",
    r"JWT_.*",  # JWT es especial
    # Variables simples de infraestructura (no requieren estructura completa)
    r".*_USUARIO$",
    r".*_PUERTO$",
    r".*_PORT$",
    r".*_THREADS$",
    r".*_ENDPOINT$",
    r".*_REMITENTE$",
    r".*_DESTINATARIOS$",
    r".*_SCOPE$",
    r".*_DIRECTORIO$",
    r".*_NIVEL$",
    r".*_FORMATO$",
    r".*_NOMBRE$",
]


def is_exempt(var_name: str) -> bool:
    """Verifica si una variable está exenta de la validación."""
    for pattern in EXEMPT_PATTERNS:
        if re.match(pattern, var_name):
            return True
    return False


def get_service_prefix(var_name: str) -> str | None:
    """Extrae el prefijo de servicio de una variable."""
    for service in sorted(VALID_SERVICES, key=len, reverse=True):
        if var_name.startswith(service + "_"):
            return service
    return None


def validate_variable_name(var_name: str) -> tuple[bool, str]:
    """
    Valida que el nombre de una variable siga la convención.

    Returns:
        (is_valid, message)
    """
    # Ignorar líneas vacías y comentarios
    if not var_name or var_name.startswith("#"):
        return True, ""

    # Verificar si está exenta
    if is_exempt(var_name):
        return True, f"✓ {var_name} (exenta)"

    # Extraer prefijo de servicio
    service = get_service_prefix(var_name)
    if not service:
        return False, f"✗ {var_name}: Prefijo de servicio no reconocido"

    # Obtener el resto después del servicio
    rest = var_name[len(service) + 1 :]  # +1 for underscore

    # Debe tener al menos 2 partes (TEMA_ACCION)
    parts = rest.split("_")
    if len(parts) < 2:
        return False, f"✗ {var_name}: Debe tener al menos SERVICIO_TEMA_ACCION"

    # Verificar si el tema es conocido (solo warning, no error)
    if service in KNOWN_THEMES:
        tema = parts[0]
        if tema not in KNOWN_THEMES[service]:
            # No es error, solo sugerencia
            pass

    return True, f"✓ {var_name}"


def parse_env_file(filepath: Path) -> list[str]:
    """Extrae nombres de variables de un archivo .env."""
    variables = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Ignorar líneas vacías y comentarios
            if not line or line.startswith("#"):
                continue
            # Extraer nombre de variable (antes del =)
            if "=" in line:
                var_name = line.split("=")[0].strip()
                variables.append(var_name)
    return variables


def main():
    strict_mode = "--strict" in sys.argv

    # Encontrar el archivo .env.example
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env.example"

    if not env_file.exists():
        print(f"⚠️  No se encontró {env_file}")
        return 0

    print(f"Validando convencion de nombres en {env_file.name}...")
    print("   Convencion: {SERVICIO}_{TEMA}_{ACCION}[_{UNIDAD}]")
    print()

    variables = parse_env_file(env_file)
    errors = []
    valid_count = 0

    for var in variables:
        is_valid, message = validate_variable_name(var)
        if not is_valid:
            errors.append(message)
            print(f"  {message}")
        else:
            valid_count += 1

    print()
    print(f"Resultado: {valid_count}/{len(variables)} variables validas")

    if errors:
        print(f"\n{len(errors)} variable(s) no siguen la convencion:")
        for error in errors:
            print(f"   {error}")

        if strict_mode:
            print("\nModo estricto: Fallo la validacion")
            return 1
        else:
            print("\nSugerencia: Ejecuta con --strict para fallar en violaciones")
            return 0

    print("\nTodas las variables siguen la convencion")
    return 0


if __name__ == "__main__":
    sys.exit(main())
