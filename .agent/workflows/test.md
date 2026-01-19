---
description: Ejecutar la suite de pruebas del proyecto
---

Ejecuta los tests utilizando `uv run pytest`. Puedes especificar el tipo de test:

1. **Todos los tests**: `uv run pytest`
2. **Unitarios**: `uv run pytest tests/unit`
3. **Integración**: `uv run pytest tests/integration`
4. **BDD (Features)**: `uv run pytest tests/features`

// turbo
uv run pytest
