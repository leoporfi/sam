# 🤖 Protocolo Maestro SAM

Eres un agente operando en un sistema RPA crítico en producción. Tu comportamiento debe estar estrictamente guiado por la documentación interna del proyecto.

## 📚 Fuente de Verdad (Source of Truth)

Antes de realizar cualquier cambio, **DEBES** consultar y seguir la jerarquía definida en:
1. AGENTS.md (Protocolo de alto nivel)
2. docs/ai/00_agents_readme.md (Guía detallada para agentes)

## 🚨 Reglas Críticas de Operación

1. **Base de Datos**: PROHIBIDO SQL crudo. Usa exclusivamente Stored Procedures (docs/ai/03_reglas_sql.md).
2. **Estilo**: Sigue estrictamente PEP 8 y las reglas de Ruff (docs/ai/02_reglas_desarrollo.md).
3. **Seguridad**: Nunca expongas credenciales ni modifiques .env sin permiso (docs/ai/04_seguridad.md).
4. **Validación**: Todo cambio de lógica debe ser validado con tests BDD (tests/features/).

## 🔍 Proceso de Trabajo

- Siempre lee el archivo docs/ai/01_arquitectura.md si vas a proponer cambios estructurales.
- Usa el **Modo Planificación** para proponer cambios antes de implementarlos.
- Si detectas una discrepancia entre el código y la documentación, la Base de Datos (SPs) y los Tests BDD mandan.
