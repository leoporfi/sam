AGENTS.MD - Contexto y Reglas del Proyecto SAM

Visión General del Proyecto

SAM (Sistema de Asignación y Monitoreo) es una plataforma RPA desarrollada en Python 3.10+ diseñada para ejecutarse en entornos Windows Server.
El sistema orquesta robots, balancea cargas de trabajo y gestiona colas mediante una arquitectura de microservicios monolíticos.

El proyecto utiliza:

Lenguaje: Python 3.10+

Gestor de Paquetes: uv (basado en pyproject.toml y uv.lock)

Base de Datos: SQL Server (Lógica de negocio en Stored Procedures)

Servicios: 4 servicios Python gestionados por NSSM (Non-Sucking Service Manager)

Servicios del Sistema

Cada servicio tiene su propio entrypoint en src/sam/ y opera como un servicio de Windows independiente.

Web (/web): Panel de control, dashboards analíticos y API Backend.

Lanzador (/lanzador): Instanciación de procesos y conciliación de estados.

Balanceador (/balanceador): Algoritmos de asignación y gestión de "cooling".

Callback (/callback): API de recepción de estados de los robots.

Reglas para Agentes de IA (IMPORTANTE)

1. Base de Datos (Regla de Oro)

NO escribir SQL crudo en Python. La lógica de negocio reside en database/procedures/.

Patrón de Acceso: Python debe llamar a Stored Procedures (SPs) existentes usando src/sam/common/database.py.

Modificaciones: Si necesitas nueva lógica de datos:

Crea/Modifica el SP en database/procedures/.

Crea el script de migración numerado en database/migrations/.

Llama al SP desde Python.

Nomenclatura: Usar nombres descriptivos en español para los procedimientos (ej: ObtenerRobotsEjecutables).

Estándar de Stored Procedures (MANDATORIO):
Todo SP que realice modificaciones (INSERT, UPDATE, DELETE) debe seguir este patrón:
- Usar `SET NOCOUNT ON;` y `SET XACT_ABORT ON;`.
- Implementar bloque `BEGIN TRY...END TRY` y `BEGIN CATCH...END CATCH`.
- En el `CATCH`, realizar `ROLLBACK` si hay transacciones activas.
- Registrar el error en `dbo.ErrorLog` (Usuario, SPNombre, ErrorMensaje, Parametros).
- Relanzar el error con `RAISERROR`.

Ejemplo de Estándar:
```sql
CREATE PROCEDURE [dbo].[EjemploSP] @Param1 INT AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRANSACTION;
        -- Lógica aquí
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        DECLARE @Msg NVARCHAR(MAX) = ERROR_MESSAGE();
        INSERT INTO dbo.ErrorLog (FechaHora, Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (GETDATE(), SUSER_NAME(), 'dbo.EjemploSP', @Msg, '@Param1=' + CAST(@Param1 AS VARCHAR));
        RAISERROR(@Msg, 16, 1);
    END CATCH
END
```

2. Infraestructura y Sistema Operativo

Entorno: Asume Windows estrictamente.

NSSM: NO modificar la configuración de servicios Windows ni los nombres de los servicios a menos que sea explícitamente solicitado.

Rutas: Usar pathlib. No hardcodear rutas absolutas (ej: C:\).

3. Gestión de Dependencias

Las dependencias se gestionan exclusivamente con uv.

pyproject.toml es la única fuente de verdad.

NO modificar uv.lock manualmente.

Si sugieres una nueva librería, asegúrate de que sea compatible con Windows.

Documentación y Versionado (MANDATORIO)

CHANGELOG.md: Todo cambio funcional, fix o mejora debe registrarse inmediatamente en CHANGELOG.md. Mantener el formato existente.

Tests BDD (.feature): Los archivos en tests/features/ son la fuente de verdad del comportamiento del negocio.

Si cambias la lógica de negocio, DEBES actualizar el escenario correspondiente en el archivo .feature.

Nunca dejes que el código contradiga a los archivos .feature.

Versionado: Respetar el versionado semántico (SemVer) y el uso correcto de tags en Git para los releases.

Estrategia de Ramas (Git):
- Nueva Característica (Feature): Crear SIEMPRE una rama nueva. Preguntar al usuario desde qué rama base se debe crear.
- Corrección Pequeña (Fix): Realizar el cambio en la rama que el usuario indique.
- Refactorización (Refactor): Crear una rama nueva solo si los cambios son complejos o afectan a múltiples componentes.


Estilo de Código y Calidad

Tipado: Usa Type Hints (typing) estrictos en todo el código nuevo.

Logging: Usa SIEMPRE src/sam/common/logging_setup.py. Nunca uses print().

Pre-commit: El proyecto utiliza hooks de pre-commit (ruff, formatters, etc.). Asegúrate de que los cambios pasen el pre-commit antes de intentar subir (uv run pre-commit run --all-files).


Estructura:

src/sam/common: Utilidades transversales.

src/sam/<modulo>/service: Lógica de negocio pura.

src/sam/<modulo>/backend o api: Capa de exposición.

Frontend (Web Service)

El frontend se genera desde Python (Server-Side Component pattern).

Estilos: Se utiliza PicoCSS (pico.violet.min.css) y dashboard.css.

Tecnología: NO introducir frameworks de JS complejos (React/Vue). Mantener la simplicidad de Python + HTML/HTMX.

Testing

Ejecutar tests con pytest.

Si modificas lógica crítica (Balanceador/Lanzador), añade un test en tests/.

NO eliminar tests existentes sin justificación.

Lo que NO debes hacer (Restricciones)

NO refactorizar múltiples servicios a la vez. Cambios localizados y atómicos.

NO cambiar la versión de Python (3.10).

NO asumir comandos de Linux (sudo, bash, rutas /etc/).

NO incluir lógica de negocio compleja en Python si se puede resolver eficientemente en un Stored Procedure.

En caso de duda

Si el contexto sobre un Stored Procedure falta, o la diferencia entre "Robots Cíclicos" vs "Online" es ambigua, consulta la carpeta docs/ antes de generar código.
