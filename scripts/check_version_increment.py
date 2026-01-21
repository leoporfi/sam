#!/usr/bin/env python3
"""
Pre-commit hook para verificar que la versión se haya incrementado
cuando se realiza un commit de tipo 'feat:' o 'fix:'.
"""

import re
import subprocess
import sys
from pathlib import Path


def get_current_version():
    """Obtiene la versión actual desde __init__.py"""
    try:
        content = Path("src/sam/__init__.py").read_text(encoding="utf-8")
        match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"[ERROR] No se pudo leer src/sam/__init__.py: {e}")
    return None


def get_last_committed_version():
    """Obtiene la versión del último commit en la rama actual"""
    try:
        # Intentar obtener la versión del HEAD
        result = subprocess.run(
            ["git", "show", "HEAD:src/sam/__init__.py"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            # Si falla (ej: primer commit), retornar None
            return None

        match = re.search(r'__version__\s*=\s*"([^"]+)"', result.stdout)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None


def get_commit_message():
    """Obtiene el mensaje del commit desde COMMIT_EDITMSG"""
    try:
        commit_msg_file = Path(".git/COMMIT_EDITMSG")
        if commit_msg_file.exists():
            return commit_msg_file.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return ""


def parse_version(version_str):
    """Parsea una versión en formato X.Y.Z"""
    try:
        parts = version_str.split(".")
        return tuple(int(p) for p in parts[:3])
    except Exception:
        return None


def version_was_incremented(old_version, new_version):
    """Verifica si la nueva versión es mayor que la anterior"""
    old = parse_version(old_version)
    new = parse_version(new_version)

    if not old or not new:
        return False

    return new > old


def main():
    # Obtener versión actual
    current_version = get_current_version()
    if not current_version:
        print("[ERROR] No se pudo determinar la versión actual")
        sys.exit(1)

    # Obtener versión del último commit
    last_version = get_last_committed_version()

    # Si no hay versión anterior (primer commit), permitir
    if not last_version:
        print(f"[OK] Primera versión detectada: {current_version}")
        sys.exit(0)

    # Obtener mensaje del commit
    commit_msg = get_commit_message()

    # Verificar si el commit es de tipo feat: o fix:
    is_feature = commit_msg.startswith("feat:")
    is_fix = commit_msg.startswith("fix:")

    if is_feature or is_fix:
        commit_type = "feat" if is_feature else "fix"

        # Verificar si la versión fue incrementada
        if current_version == last_version:
            print(f"\n{'=' * 70}")
            print(f"[ERROR] Commit de tipo '{commit_type}:' requiere incremento de versión")
            print(f"{'=' * 70}")
            print(f"Versión actual:  {current_version}")
            print(f"Versión anterior: {last_version}")
            print("\nPara commits 'feat:' incrementa MINOR (ej: 1.8.5 → 1.9.0)")
            print("Para commits 'fix:' incrementa PATCH (ej: 1.8.5 → 1.8.6)")
            print("\nEdita: src/sam/__init__.py")
            print(f"{'=' * 70}\n")
            sys.exit(1)

        if not version_was_incremented(last_version, current_version):
            print(f"\n{'=' * 70}")
            print("[ERROR] La nueva versión debe ser mayor que la anterior")
            print(f"{'=' * 70}")
            print(f"Versión actual:   {current_version}")
            print(f"Versión anterior: {last_version}")
            print(f"{'=' * 70}\n")
            sys.exit(1)

        print(f"[OK] Versión incrementada: {last_version} → {current_version}")
    else:
        print(f"[OK] Commit tipo '{commit_msg.split(':')[0]}:' no requiere cambio de versión")

    sys.exit(0)


if __name__ == "__main__":
    main()
