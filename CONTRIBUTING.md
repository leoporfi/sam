# Guía de Contribución

## Flujo de Trabajo
1. **Ramas**: Crea una rama desde `develop`: `git checkout -b feature/mi-nueva-feature`.
   - `feature/`: Nuevas funcionalidades.
   - `fix/`: Corrección de errores.
   - `hotfix/`: Urgencias en producción.
2. **Entorno**: Instala el entorno con `uv sync`.
3. **Hooks**: Activa los hooks con `pre-commit install`.

## Estándares
- **Python**: Seguimos PEP8. Ejecuta `ruff check .` antes de subir.
- **Commits**: Usa el formato [Conventional Commits](https://www.conventionalcommits.org/).
  - `feat`: Nueva funcionalidad
  - `fix`: Corrección de errores
  - `refactor`: Cambio de código que no altera funcionalidad
  - `docs`: Cambios en documentación
  - `chore`: Tareas de mantenimiento

## Base de Datos
- **Stored Procedures**: Si modificas la BD, debes crear/actualizar el SP correspondiente en `database/sps/`.
- **SQL en Python**: PROHIBIDO usar SQL directo en código Python. Siempre usa Stored Procedures.

## Pull Requests
- Deben tener una descripción clara de los cambios.
- Deben pasar todos los tests locales y validaciones de pre-commit.
