# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.16.3] - 2026-01-30

### Fixed
- **Interfaz Web - Estabilidad en AnalyticsSummary**: Corregido un error de `NoneType` que ocurría al cancelar la carga de datos (al navegar rápido entre páginas). Ahora se maneja correctamente el ciclo de vida asíncrono.
- **Interfaz Web - Mayor limpieza de logs**: Se agregó el aviso de asyncio `Task was destroyed but it is pending!` al filtro de logs, ya que es un efecto secundario inofensivo del desmontaje de componentes en ReactPy.

## [1.16.2] - 2026-01-30

### Fixed
- **Interfaz Web - Silenciado de errores ReactPy en logs**: Implementación de un filtro de logs (`ReactPyErrorFilter`) y reducción del nivel de log a `CRITICAL` para los módulos internos de ReactPy (`reactpy.core`, `reactpy.backend`) con el fin de evitar ruidos persistentes causados por el bug de concurrencia de la librería en producción.

## [1.16.1] - 2026-01-30

### Fixed
- **Interfaz Web - Mitigación de errores ReactPy en producción**: Agregados límites de conexión (`limit_concurrency=50`) y timeout de keep-alive (`timeout_keep_alive=10s`) en Uvicorn para mitigar errores `Hook stack is in an invalid state` y `Layout object has no attribute _rendering_queue` causados por concurrencia de múltiples usuarios (~30 conexiones).
  - Nuevas variables de configuración: `INTERFAZ_WEB_LIMITE_CONEXIONES`, `INTERFAZ_WEB_TIMEOUT_KEEPALIVE_SEG`
  - Actualizado `ConfigManager` y `run_web.py` para aplicar estos límites

## [1.16.0] - 2026-01-30

### Added
- **Validación Automática de Configuración**: Introducción de `scripts/check_env_naming.py` y hook de pre-commit para asegurar la adherencia a la nueva convención de nombres.
- **Migración de Base de Datos**: Script SQL para renombrar claves de configuración existentes de forma segura (`migracion_renombrar_claves_v2.sql`).

### Changed
- **Reorganización Semántica de Variables**: Implementación de la convención `{SERVICIO}_{TEMA}_{ACCION}[_{UNIDAD}]` para más de 80 variables, mejorando el agrupamiento alfabético.
- **ConfigManager con Fallback**: Soporte para compatibilidad hacia atrás, permitiendo el uso de nombres antiguos y nuevos simultáneamente.
- **Mejoras en Interfaz Web**:
    - El modal de edición de configuración ahora mantiene el valor actual al abrirse.
    - Agregado de placeholders descriptivos dinámicos según el tipo de variable.
    - Estandarización visual de acciones en la tabla de configuración para coincidir con el resto del dashboard.

## [1.15.0] - 2026-01-29

### Added
- **Mejoras en Configuración Dinámica**: Se ha incrementado la versión para reflejar mejoras significativas en la gestión de configuración.

## [1.14.0] - 2026-01-29

### Added
- **Mejoras en Configuración Dinámica**: Se ha incrementado la versión para reflejar mejoras significativas en la gestión de configuración.


### Changed
- **Refactorización de Variables**: Corrección en `EMAIL_DESTINATARIOS` (removido prefijo `LANZADOR_`) para mayor claridad.
- **Documentación**: Actualización del sistema de alertas, reglas de agente, glosario y FAQ.

## [1.8.5] - 2026-01-21

### Fixed
- **Lanzador - Manejo de Error 400 (No Default Device)**: Se ha mejorado la lógica para detectar el error "None of the user(s) provided have default device(s)" en A360. Ahora el sistema envía una alerta crítica con instrucciones de solución pero **mantiene la asignación activa** en SAM, evitando la necesidad de re-asignación manual tras corregir la configuración en el Control Room. Se incluyó un cooldown de 1 hora para esta alerta.

## [1.8.4] - 2026-01-20

### Added
- **Consolidación de Versión de Python**: Se ha establecido `pyproject.toml` como la única fuente de verdad para la versión de Python (`requires-python = ">=3.10"`).

### Changed
- **Documentación de Agentes**: Actualizadas todas las referencias de versión de Python para apuntar a `pyproject.toml`.
- **Configuración de Proyecto**: Elevado el requerimiento de Python a 3.10 en `pyproject.toml`.

## [1.8.3] - 2026-01-18

### Added
- **Nuevos Stored Procedures**: Implementación de SPs estandarizados para Robots, Equipos, Asignaciones, Programaciones, Mapeos y Configuración.
- **Estándar de SPs en AGENTS.md**: Definición obligatoria de manejo de errores, transacciones y logging en `dbo.ErrorLog` para todos los SPs.
- **Estrategia de Ramas**: Documentación de la estrategia de Git en `AGENTS.md`.

### Changed
- **Refactorización de Web Service**: Eliminación total de SQL crudo en `src/sam/web/backend/database.py`, sustituyéndolo por llamadas a Stored Procedures.
- **Gestión de Asignaciones**: Migración a Table-Valued Parameters (TVPs) para la actualización de asignaciones de robots.
- **Tolerancia en Conciliador**: Implementación de un periodo de gracia (intentos configurables) antes de inferir la finalización de ejecuciones desaparecidas en A360, reduciendo falsos positivos.

## [1.8.2] - 2026-01-16

### Fixed
- Correcciones menores en la sincronización de estados.

## [1.5.0] - 2026-01-11

### Added
- **Sistema de Alertas Inteligentes**: Implementación de clasificación tridimensional de alertas (Severidad, Alcance, Naturaleza).
- **Detección de Patrones de Reinicio A360**: Lógica para identificar reinicios de servicios (errores 5xx múltiples) y suprimir alertas redundantes, enviando un aviso de recuperación (RECOVERY) en lugar de múltiples alertas críticas.
- **Formato de Email Mejorado**: Nuevas plantillas HTML con badges de clasificación, secciones estructuradas (Contexto Técnico, Acciones) y tracking de frecuencia.
- **Tracking de Frecuencia**: Control de repetición de alertas persistentes (ej. cada 30 min) para evitar fatiga de alertas.

### Changed
- **Refactorización de Alertas en Desplegador**: Migración de alertas 412, 400 y 500 al nuevo sistema `send_alert_v2`.
- **Refactorización de Alertas en Orquestador**: Migración de alerta de umbral 412 al nuevo sistema.

## [1.3.3] - 2026-01-05

### Fixed
- **Interfaz Web - Búsqueda con Enter en lugar de debounce**: Corregido el problema donde las letras se borraban mientras el usuario escribía en los campos de búsqueda. Se eliminó el debounce automático y se implementó búsqueda manual con Enter. Ahora los usuarios pueden escribir sin interferencias y la búsqueda se ejecuta solo al presionar Enter, mejorando significativamente la experiencia de usuario. Se aplicó a las páginas de Robots y Equipos.

### Changed
- **Interfaz Web - Comportamiento de búsqueda**: Cambiado de búsqueda automática con debounce (300ms) a búsqueda manual con Enter. Los campos de búsqueda ahora muestran el placeholder "(Presiona Enter)" para indicar el nuevo comportamiento.

## [1.3.2] - 2026-01-05

### Fixed
- **Lanzador - Alertas por correo para errores HTTP 500**: Corregido el problema donde los errores HTTP 500 del servidor A360 no generaban alertas por correo electrónico. Ahora el sistema envía alertas críticas automáticamente cuando ocurren errores del servidor (5xx), incluyendo información detallada del robot, equipo, usuario y mensaje de error completo. Se implementó control de alertas para evitar spam en el mismo ciclo de despliegue.

## [1.3.1] - 2026-01-05

### Fixed
- **Interfaz Web - Limpieza de tareas asíncronas**: Corregido el manejo de limpieza de tareas asíncronas en `use_debounced_value_hook` para evitar el error "Task was destroyed but it is pending" cuando los componentes se desmontan. Se implementó rastreo de estado de montaje y limpieza adecuada de tareas para prevenir condiciones de carrera y errores de hook stack inválido.

## [1.3.0] - 2026-01-05

### Added
- **Mejoras en sistema de alertas por correo**:
  - Escape de HTML en subject y message para prevenir inyección de código
  - Formato HTML mejorado con estilos CSS inline para mejor presentación
  - Timestamp formateado en cada mensaje de alerta
  - Stack traces completos en alertas de errores críticos para facilitar debugging
  - Verificación del resultado de envío de alertas con logging de fallos
  - Inclusión del nombre del equipo (además del ID) en alertas 412 persistentes

### Changed
- Estandarización del uso de argumentos con nombre en todas las llamadas a `send_alert`
- Mejora en el manejo de errores cuando falla el envío de alertas (no marca como alertado si falla)

## [1.2.0] - 2026-01-04

### Added
- **Soporte para Robots Cíclicos**: Implementación completa de ejecuciones cíclicas con ventanas de tiempo, intervalos configurables y lógica de reintentos.
- **Mejora en alertas por email**: Los mensajes ahora incluyen nombres legibles (Robot, Equipo, Usuario) además de los IDs para facilitar la identificación rápida de incidentes.
- Emojis y formato enriquecido en los correos de alerta (🤖, 💻, 👤, 📋, ⚠️).
- Asuntos de correo más descriptivos incluyendo nombres de robot y equipo.
- **Mejoras en Interfaz Web**: Estandarización de componentes ReactPy y nuevas validaciones de valores mínimos/máximos en los modales de configuración de robots.
- Aumento del tamaño de página por defecto (`PAGE_SIZE`) a 100 en múltiples hooks y consultas de base de datos.

### Changed
- **Optimización SQL**: Eliminado JOIN redundante en el Stored Procedure `dbo.ObtenerRobotsEjecutables`.
- El Stored Procedure `dbo.ObtenerRobotsEjecutables` ahora retorna 7 columnas (agregadas: `Robot`, `Equipo`, `UserName`). El `UserName` se obtiene directamente de la tabla `Equipos`.

### Fixed
- **Visualización de Estados**: Corregida la visualización de estados de equipos en los modales y listas principales de la web.
- Mejora en la observabilidad de errores 400 y 412 en el módulo Desplegador.
- Corrección de múltiples errores de linting (Ruff) reportados por los pre-commit hooks.
