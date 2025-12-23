#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de verificación para el fix de hooks de ReactPy.

Este script verifica que los cambios aplicados para corregir el error
"Hook stack is in an invalid state" están correctamente implementados.

Uso:
    python scripts/verificar_fix_hooks.py
    python scripts/verificar_fix_hooks.py --log-path logs/sam_interfaz_web.log
"""

import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Configurar encoding para Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# Colores para output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str):
    """Imprime un encabezado formateado."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}\n")


def print_success(text: str):
    """Imprime un mensaje de éxito."""
    print(f"{Colors.GREEN}[OK] {text}{Colors.RESET}")


def print_error(text: str):
    """Imprime un mensaje de error."""
    print(f"{Colors.RED}[ERROR] {text}{Colors.RESET}")


def print_warning(text: str):
    """Imprime un mensaje de advertencia."""
    print(f"{Colors.YELLOW}[WARN] {text}{Colors.RESET}")


def print_info(text: str):
    """Imprime un mensaje informativo."""
    print(f"  {text}")


class HookVerifier:
    """Verificador de hooks de ReactPy."""

    # Hooks de ReactPy que deben llamarse incondicionalmente
    REACTPY_HOOKS = [
        "use_state",
        "use_effect",
        "use_context",
        "use_callback",
        "use_memo",
        "use_ref",
        "use_app_context",  # Hook personalizado
        "use_debounced_value",  # Hook personalizado
        "use_robots",
        "use_equipos",
        "use_pools_management",
        "use_schedules",
    ]

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.hooks_dir = project_root / "src" / "sam" / "web" / "frontend" / "hooks"
        self.results: Dict[str, List[str]] = {
            "errors": [],
            "warnings": [],
            "success": [],
        }

    def verify_file_syntax(self, file_path: Path) -> bool:
        """Verifica que el archivo tiene sintaxis Python válida."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                ast.parse(f.read(), filename=str(file_path))
            return True
        except SyntaxError as e:
            self.results["errors"].append(f"{file_path.name}: Error de sintaxis en línea {e.lineno}: {e.msg}")
            return False
        except Exception as e:
            self.results["errors"].append(f"{file_path.name}: Error al leer archivo: {e}")
            return False

    def find_conditional_hook_calls(self, file_path: Path) -> List[Tuple[int, str]]:
        """
        Busca llamadas a hooks dentro de bloques condicionales.
        Retorna lista de (línea, hook_name) encontrados.
        """
        issues = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

            # Buscar patrones problemáticos
            in_conditional = False
            conditional_depth = 0
            indent_level = 0

            for i, line in enumerate(lines, 1):
                stripped = line.strip()

                # Detectar inicio de bloque condicional
                if re.match(r"^\s*(if|elif|else)\s+.*:", stripped):
                    in_conditional = True
                    indent_level = len(line) - len(line.lstrip())

                # Detectar fin de bloque condicional (línea con menor indentación)
                if in_conditional and stripped:
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent <= indent_level and not re.match(
                        r"^\s*(if|elif|else|try|except|finally|with|for|while|def|class)\s+.*:", stripped
                    ):
                        in_conditional = False

                # Buscar llamadas a hooks dentro de condicionales
                if in_conditional:
                    for hook in self.REACTPY_HOOKS:
                        # Patrón: hook_name( o hook_name = hook_name(
                        pattern = rf"\b{re.escape(hook)}\s*\("
                        if re.search(pattern, line):
                            issues.append((i, hook))
                            break

        except Exception as e:
            self.results["errors"].append(f"{file_path.name}: Error al analizar: {e}")

        return issues

    def verify_hook_order(self, file_path: Path) -> bool:
        """
        Verifica que use_app_context() se llama antes de cualquier if api_client is None.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

            use_app_context_line = None
            if_api_client_line = None

            for i, line in enumerate(lines, 1):
                if "use_app_context()" in line and use_app_context_line is None:
                    use_app_context_line = i
                if "if api_client is None:" in line and if_api_client_line is None:
                    if_api_client_line = i

            if if_api_client_line is not None:
                if use_app_context_line is None:
                    self.results["errors"].append(f"{file_path.name}: No se encontró use_app_context() pero hay verificación de api_client")
                    return False
                elif use_app_context_line > if_api_client_line:
                    self.results["errors"].append(
                        f"{file_path.name}: use_app_context() está después de 'if api_client is None:' "
                        f"(línea {use_app_context_line} vs {if_api_client_line})"
                    )
                    return False
                else:
                    # Verificar que use_app_context() está fuera de un if
                    # Buscar el if más cercano antes de use_app_context
                    before_hook = "\n".join(lines[:use_app_context_line])
                    # Buscar si hay un 'if' sin cerrar antes
                    if_count = before_hook.count("if ")
                    else_count = before_hook.count("else:")
                    if if_count > else_count:
                        # Hay un if abierto, verificar indentación
                        hook_indent = len(lines[use_app_context_line - 1]) - len(lines[use_app_context_line - 1].lstrip())
                        # Buscar el último if antes de esta línea
                        for j in range(use_app_context_line - 2, -1, -1):
                            if "if " in lines[j] and ":" in lines[j]:
                                if_indent = len(lines[j]) - len(lines[j].lstrip())
                                if hook_indent > if_indent:
                                    self.results["errors"].append(
                                        f"{file_path.name}: use_app_context() está dentro de un bloque condicional (línea {use_app_context_line})"
                                    )
                                    return False
                                break

            return True

        except Exception as e:
            self.results["errors"].append(f"{file_path.name}: Error al verificar orden: {e}")
            return False

    def verify_all_hooks(self) -> bool:
        """Verifica todos los archivos de hooks."""
        print_header("Verificando archivos de hooks")

        hook_files = [
            "use_robots_hook.py",
            "use_equipos_hook.py",
            "use_pools_hook.py",
            "use_schedules_hook.py",
        ]

        all_ok = True

        for hook_file in hook_files:
            file_path = self.hooks_dir / hook_file
            if not file_path.exists():
                self.results["errors"].append(f"Archivo no encontrado: {hook_file}")
                all_ok = False
                continue

            print_info(f"Verificando {hook_file}...")

            # 1. Verificar sintaxis
            if not self.verify_file_syntax(file_path):
                all_ok = False
                continue

            # 2. Verificar orden de hooks
            if not self.verify_hook_order(file_path):
                all_ok = False
                continue

            # 3. Buscar hooks condicionales (más estricto)
            conditional_hooks = self.find_conditional_hook_calls(file_path)
            if conditional_hooks:
                for line, hook in conditional_hooks:
                    self.results["warnings"].append(f"{hook_file}: Posible hook condicional en línea {line}: {hook}")
            else:
                self.results["success"].append(f"{hook_file}: [OK] Orden de hooks correcto")

        return all_ok

    def check_logs_for_errors(self, log_path: Path = None) -> bool:
        """Busca errores de hooks en los logs."""
        print_header("Verificando logs para errores de hooks")

        if log_path is None:
            log_path = self.project_root / "logs" / "sam_interfaz_web.log"

        if not log_path.exists():
            print_warning(f"Log no encontrado: {log_path}")
            print_info("Omitiendo verificación de logs")
            return True

        error_patterns = [
            r"Hook stack is in an invalid state",
            r"RuntimeError.*Hook",
            r"Failed to render.*Hook",
        ]

        found_errors = []
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            # Buscar en las últimas 500 líneas (más recientes)
            recent_lines = lines[-500:] if len(lines) > 500 else lines

            for i, line in enumerate(recent_lines, start=len(lines) - len(recent_lines) + 1):
                for pattern in error_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        found_errors.append((i, line.strip()))

            if found_errors:
                print_error(f"Se encontraron {len(found_errors)} errores relacionados con hooks:")
                for line_num, line_content in found_errors[:10]:  # Mostrar solo los primeros 10
                    print_info(f"  Línea {line_num}: {line_content[:100]}...")
                if len(found_errors) > 10:
                    print_info(f"  ... y {len(found_errors) - 10} más")
                return False
            else:
                print_success("No se encontraron errores de hooks en los logs recientes")
                return True

        except Exception as e:
            self.results["warnings"].append(f"Error al leer log: {e}")
            return True

    def generate_report(self) -> None:
        """Genera un reporte final."""
        print_header("Reporte de Verificación")

        total_checks = len(self.results["success"]) + len(self.results["errors"]) + len(self.results["warnings"])

        if self.results["success"]:
            print(f"\n{Colors.GREEN}[OK] Verificaciones exitosas ({len(self.results['success'])}):{Colors.RESET}")
            for msg in self.results["success"]:
                print(f"  {msg}")

        if self.results["warnings"]:
            print(f"\n{Colors.YELLOW}[WARN] Advertencias ({len(self.results['warnings'])}):{Colors.RESET}")
            for msg in self.results["warnings"]:
                print(f"  {msg}")

        if self.results["errors"]:
            print(f"\n{Colors.RED}[ERROR] Errores ({len(self.results['errors'])}):{Colors.RESET}")
            for msg in self.results["errors"]:
                print(f"  {msg}")

        print(f"\n{Colors.BOLD}Resumen:{Colors.RESET}")
        print(f"  Total de verificaciones: {total_checks}")
        print(f"  {Colors.GREEN}[OK] Exitosas: {len(self.results['success'])}{Colors.RESET}")
        print(f"  {Colors.YELLOW}[WARN] Advertencias: {len(self.results['warnings'])}{Colors.RESET}")
        print(f"  {Colors.RED}[ERROR] Errores: {len(self.results['errors'])}{Colors.RESET}")

        if self.results["errors"]:
            print(f"\n{Colors.RED}{Colors.BOLD}[X] VERIFICACION FALLIDA{Colors.RESET}")
            sys.exit(1)
        elif self.results["warnings"]:
            print(f"\n{Colors.YELLOW}{Colors.BOLD}[!] VERIFICACION COMPLETA CON ADVERTENCIAS{Colors.RESET}")
            sys.exit(0)
        else:
            print(f"\n{Colors.GREEN}{Colors.BOLD}[OK] VERIFICACION EXITOSA{Colors.RESET}")
            sys.exit(0)


def main():
    """Función principal."""
    import argparse

    parser = argparse.ArgumentParser(description="Verifica el fix de hooks de ReactPy")
    parser.add_argument(
        "--log-path",
        type=Path,
        help="Ruta al archivo de log (default: logs/sam_interfaz_web.log)",
    )
    parser.add_argument(
        "--skip-logs",
        action="store_true",
        help="Omitir verificación de logs",
    )

    args = parser.parse_args()

    # Determinar el directorio raíz del proyecto
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("=" * 70)
    print("  Script de Verificación - Fix de Hooks ReactPy")
    print("=" * 70)
    print(f"{Colors.RESET}")

    verifier = HookVerifier(project_root)

    # Verificar hooks
    hooks_ok = verifier.verify_all_hooks()

    # Verificar logs (opcional)
    if not args.skip_logs:
        logs_ok = verifier.check_logs_for_errors(args.log_path)
    else:
        print_header("Verificación de logs omitida")
        logs_ok = True

    # Generar reporte
    verifier.generate_report()


if __name__ == "__main__":
    main()
