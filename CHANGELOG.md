# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
