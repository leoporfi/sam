---
description: Realizar un commit de los cambios actuales siguiendo las convenciones del proyecto
---

Sigue estos pasos para realizar un commit:

1.  **Analizar Cambios**:
    Ejecuta `git status` para ver qué archivos se han modificado.
    ```bash
    git status
    ```

2.  **Determinar Tipo y Mensaje**:
    Basado en los cambios, elige el prefijo adecuado según `.agent/rules/commit-convention.md`:
    *   `feat:` Nueva funcionalidad
    *   `fix:` Corrección de errores
    *   `docs:` Documentación
    *   `db:` Base de datos
    *   `refactor:` Refactorización
    *   `test:` Tests

    Redacta un mensaje conciso y descriptivo (ej: `feat: agregar sistema de alertas`).

    **IMPORTANTE**: Si el commit es de tipo `feat:` o `fix:`, debes incrementar la versión en `src/sam/__init__.py`:
    *   `feat:` → Incrementa MINOR (ej: 1.8.5 → 1.9.0)
    *   `fix:` → Incrementa PATCH (ej: 1.8.5 → 1.8.6)

3.  **Staging**:
    Agrega los archivos al stage. Generalmente todo:
    ```bash
    git add .
    ```

4.  **Commit**:
    Ejecuta el commit con el mensaje generado.
    ```bash
    git commit -m "tipo: mensaje descriptivo"
    ```

5.  **Verificación y Re-intento**:
    Si el commit falla debido a `pre-commit` hooks, pueden ocurrir dos casos:

    **Caso A: Correcciones automáticas (linting, formateo)**
    Los hooks modificaron archivos automáticamente:
    1.  Ejecuta `git status` para confirmar que hay cambios no stageados.
    2.  Ejecuta `git add .` para incluir las correcciones automáticas.
    3.  Ejecuta el commit nuevamente con el mismo mensaje.
    ```bash
    git add .
    git commit -m "tipo: mensaje descriptivo"
    ```

    **Caso B: Falta incremento de versión**
    Si el commit es `feat:` o `fix:` y no incrementaste la versión, verás un error como:
    ```
    [ERROR] Commit de tipo 'feat:' requiere incremento de versión
    Versión actual:  1.8.5
    Versión anterior: 1.8.5
    ```
    En este caso:
    1.  Edita `src/sam/__init__.py` e incrementa `__version__`
    2.  Ejecuta `git add src/sam/__init__.py`
    3.  Ejecuta el commit nuevamente
    ```bash
    git add src/sam/__init__.py
    git commit -m "tipo: mensaje descriptivo"
    ```
