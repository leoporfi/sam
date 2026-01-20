---
description: Ejecutar linters y formateo de código
---

Asegura que el código cumple con los estándares de Ruff y pre-commit.

1. **Verificar y corregir**: `uv run ruff check --fix src/`
2. **Formatear**: `uv run ruff format src/`
3. **Pre-commit completo**: `uv run pre-commit run --all-files`

// turbo
uv run pre-commit run --all-files
