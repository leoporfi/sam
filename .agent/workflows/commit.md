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

5.  **Verificación**:
    Si el commit falla debido a `pre-commit` hooks (linting, formateo), corrige los errores reportados y repite desde el paso 3.
