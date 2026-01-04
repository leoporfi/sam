# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] - 2026-01-04

### Added
- **Mejora en alertas por email**: Los mensajes ahora incluyen nombres legibles (Robot, Equipo, Usuario) además de los IDs para facilitar la identificación rápida de incidentes.
- Emojis y formato enriquecido en los correos de alerta (🤖, 💻, 👤, 📋, ⚠️).
- Asuntos de correo más descriptivos incluyendo nombres de robot y equipo.

### Changed
- **Optimización SQL**: Eliminado JOIN redundante en el Stored Procedure `dbo.ObtenerRobotsEjecutables`.
- El Stored Procedure `dbo.ObtenerRobotsEjecutables` ahora retorna 7 columnas (agregadas: `Robot`, `Equipo`, `UserName`). El `UserName` se obtiene directamente de la tabla `Equipos`.

### Fixed
- Mejora en la observabilidad de errores 400 y 412 en el módulo Desplegador.
