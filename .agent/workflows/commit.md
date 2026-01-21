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

5.  **Verificación y Re-intento**:
    Si el commit falla debido a `pre-commit` hooks (linting, formateo), es muy probable que los hooks hayan modificado archivos para corregirlos.
    En este caso:
    1.  Ejecuta `git status` para confirmar que hay cambios no stageados.
    2.  Ejecuta `git add .` para incluir las correcciones automáticas.
    3.  Ejecuta el commit nuevamente con el mismo mensaje.
    ```bash
    git add .
    git commit -m "tipo: mensaje descriptivo"
    ```
