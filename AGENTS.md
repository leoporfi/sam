# **🤖 SAM \- Protocolo para Agentes de IA**

Este proyecto es un Orquestador RPA Crítico en producción (Windows/Python/SQL Server).
No es un CRUD simple. Los errores aquí detienen operaciones de negocio reales.

## **🚦 MAPA DE REGLAS (Source of Truth)**

Para realizar cualquier tarea, **DEBES** consultar la guía específica en docs/ai/:

| Si vas a tocar... | Consulta OBLIGATORIAMENTE... |
| :---- | :---- |
| **Entender el sistema** | 🏛️ [docs/ai/01_arquitectura.md](docs/ai/01_arquitectura.md) |
| **Código Python / Web** | 🐍 [docs/ai/02_reglas_desarrollo.md](docs/ai/02_reglas_desarrollo.md) |
| **Base de Datos / SPs** | 🗄️ [docs/ai/03_reglas_sql.md](docs/ai/03_reglas_sql.md) |
| **Seguridad / Credenciales** | 🔒 [docs/ai/04_seguridad.md](docs/ai/04_seguridad.md) |
| **Diagnóstico / Tareas** | 🛠️ [docs/ai/05_ejemplos_tareas.md](docs/ai/05_ejemplos_tareas.md) |
| **Alertas / Notificaciones** | 🚨 [docs/ai/08_alertas.md](docs/ai/08_alertas.md) |

## **⛔ REGLAS DE ORO (Hard Rules)**

1. **Base de Datos:** PROHIBIDO SQL crudo en Python. Usa Stored Procedures.
2. **Infraestructura:** NO toques configuración de NSSM ni servicios de Windows sin permiso explícito.
3. **Dependencias:** Usa estrictamente uv y pyproject.toml.
4. **Verdad:** Los archivos .feature en tests/ mandan sobre el código.

**¿Dudas?** Si la tarea implica borrar datos, cambiar lógica core o tocar credenciales, DETENTE y pide confirmación.
