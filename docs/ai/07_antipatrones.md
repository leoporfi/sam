# ⚠️ ANTIPATRONES - PROYECTO SAM

---
**Versión:** 1.0.0
**Última Actualización:** 2025-01-19
---

## 🎯 PROPÓSITO

Este documento cataloga **errores comunes** y **malas prácticas** observadas en el desarrollo y operación de SAM. Cada antipatrón incluye:
- ❌ Ejemplo del error
- 🔍 Por qué es problemático
- ✅ Solución correcta

---

## 📋 ÍNDICE

1. [Antipatrones de Base de Datos](#1-antipatrones-de-base-de-datos)
2. [Antipatrones de Python](#2-antipatrones-de-python)
3. [Antipatrones de Configuración](#3-antipatrones-de-configuración)
4. [Antipatrones de Operación](#4-antipatrones-de-operación)
5. [Antipatrones de Seguridad](#5-antipatrones-de-seguridad)

---

## 1. ANTIPATRONES DE BASE DE DATOS

### ❌ SQL Crudo en Python

**Problema:**
```python
# MAL: SQL crudo con f-strings
robot_name = "Proceso_Pagos"
query = f"SELECT * FROM Robots WHERE Nombre = '{robot_name}'"
cursor.execute(query)
```

**Por qué es malo:**
- 🔴 **Inyección SQL**: Vulnerable a ataques
- 🔴 **Lógica duplicada**: Reglas de negocio en Python y SQL
- 🔴 **Mantenimiento**: Cambios requieren modificar código Python
- 🔴 **Testing**: Difícil de probar sin BD

**Solución:**
```python
# BIEN: Usar Stored Procedure
await db.execute_sp(
    "dbo.ObtenerRobotPorNombre",
    {"Nombre": robot_name}
)
```

**Referencias:** [03_reglas_sql.md](03_reglas_sql.md)

---

### ❌ Stored Procedures Sin Manejo de Errores

**Problema:**
```sql
-- MAL: Sin TRY...CATCH
CREATE PROCEDURE dbo.ActualizarRobot
    @RobotId INT,
    @Nombre NVARCHAR(100)
AS
BEGIN
    UPDATE dbo.Robots
    SET Nombre = @Nombre
    WHERE RobotId = @RobotId;
END
```

**Por qué es malo:**
- 🔴 **Sin trazabilidad**: Errores no se registran
- 🔴 **Transacciones huérfanas**: Pueden quedar locks
- 🔴 **Debugging imposible**: No hay información del error

**Solución:**
```sql
-- BIEN: Con manejo de errores estándar
CREATE PROCEDURE dbo.ActualizarRobot
    @RobotId INT,
    @Nombre NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @ErrorMessage NVARCHAR(4000);

    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE dbo.Robots
        SET Nombre = @Nombre
        WHERE RobotId = @RobotId;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        SET @ErrorMessage = ERROR_MESSAGE();

        INSERT INTO dbo.ErrorLog (Procedimiento, Mensaje, FechaRegistro)
        VALUES ('dbo.ActualizarRobot', @ErrorMessage, GETDATE());

        RAISERROR(@ErrorMessage, 16, 1);
    END CATCH
END
```

**Referencias:** [03_reglas_sql.md](03_reglas_sql.md)

---

### ❌ Modificar Datos Sin Auditoría

**Problema:**
```sql
-- MAL: UPDATE directo sin registro
UPDATE dbo.Ejecuciones
SET Estado = 'COMPLETED'
WHERE EjecucionId = 12345;
```

**Por qué es malo:**
- 🔴 **Sin trazabilidad**: No se sabe quién/cuándo modificó
- 🔴 **Compliance**: Viola auditoría
- 🔴 **Debugging**: Imposible rastrear cambios manuales

**Solución:**
```sql
-- BIEN: Registrar en tabla de auditoría
BEGIN TRANSACTION;

-- Guardar estado anterior
INSERT INTO dbo.AuditoriaManual (Tabla, RegistroId, CampoModificado, ValorAnterior, ValorNuevo, Usuario, Justificacion)
SELECT
    'Ejecuciones',
    12345,
    'Estado',
    Estado,
    'COMPLETED',
    SUSER_NAME(),
    'Corrección manual por timeout A360'
FROM dbo.Ejecuciones
WHERE EjecucionId = 12345;

-- Realizar cambio
UPDATE dbo.Ejecuciones
SET Estado = 'COMPLETED', FechaFin = GETDATE()
WHERE EjecucionId = 12345;

COMMIT TRANSACTION;
```

**Referencias:** [04_seguridad.md](04_seguridad.md#3-acceso-a-base-de-datos)

---

## 2. ANTIPATRONES DE PYTHON

### ❌ Usar `print()` en Lugar de Logging

**Problema:**
```python
# MAL: Debugging con print
def deploy_robot(robot):
    print(f"Desplegando robot: {robot.name}")
    try:
        result = api_client.deploy(robot)
        print(f"Éxito: {result}")
    except Exception as e:
        print(f"Error: {e}")
```

**Por qué es malo:**
- 🔴 **No persiste**: Se pierde al cerrar terminal
- 🔴 **Sin niveles**: No se puede filtrar por severidad
- 🔴 **Sin contexto**: No incluye timestamp, servicio, etc.
- 🔴 **Producción**: Invisible en servicios de Windows

**Solución:**
```python
# BIEN: Usar logger configurado
from sam.common.logging_setup import setup_logger

logger = setup_logger("lanzador")

def deploy_robot(robot):
    logger.info(f"Desplegando robot: {robot.name}", extra={"robot_id": robot.id})
    try:
        result = api_client.deploy(robot)
        logger.info(f"Robot desplegado exitosamente", extra={"deployment_id": result.id})
    except Exception as e:
        logger.error(f"Fallo al desplegar robot {robot.name}", exc_info=True)
```

**Referencias:** [02_reglas_desarrollo.md](02_reglas_desarrollo.md#3-logging)

---

### ❌ Código Bloqueante en Event Loop Asíncrono

**Problema:**
```python
# MAL: Operación bloqueante en async
async def process_robots(robots):
    for robot in robots:
        result = requests.post(url, json=robot)  # ❌ Bloqueante
        await asyncio.sleep(1)
```

**Por qué es malo:**
- 🔴 **Bloquea event loop**: Detiene TODAS las tareas asíncronas
- 🔴 **Performance**: Pierde beneficio de concurrencia
- 🔴 **Timeouts**: Puede causar timeouts en otros servicios

**Solución:**
```python
# BIEN: Usar cliente asíncrono
async def process_robots(robots):
    async with httpx.AsyncClient() as client:
        tasks = [client.post(url, json=robot) for robot in robots]
        results = await asyncio.gather(*tasks)
```

**Referencias:** [02_reglas_desarrollo.md](02_reglas_desarrollo.md#6-asyncawait)

---

### ❌ Sin Tipado Estático

**Problema:**
```python
# MAL: Sin type hints
def get_robots(active_only=True):
    results = []
    # ...
    return results
```

**Por qué es malo:**
- 🔴 **Mantenimiento**: Difícil entender qué espera/retorna
- 🔴 **Bugs**: Errores de tipo solo en runtime
- 🔴 **IDE**: Sin autocompletado ni ayuda

**Solución:**
```python
# BIEN: Con tipado completo
from typing import List, Dict, Optional

def get_robots(active_only: bool = True) -> List[Dict[str, any]]:
    results: List[Dict[str, any]] = []
    # ...
    return results
```

**Referencias:** [02_reglas_desarrollo.md](02_reglas_desarrollo.md#2-tipado-estático)

---

### ❌ Capturar Excepciones Genéricas

**Problema:**
```python
# MAL: Captura genérica sin logging
try:
    deploy_robot(robot)
except:  # ❌ Nunca usar except sin tipo
    pass  # ❌ Silenciar errores
```

**Por qué es malo:**
- 🔴 **Debugging imposible**: No se sabe qué falló
- 🔴 **Oculta bugs**: Errores críticos pasan desapercibidos
- 🔴 **Captura TODO**: Incluso `KeyboardInterrupt`

**Solución:**
```python
# BIEN: Captura específica con logging
from sam.common.exceptions import DeploymentError

try:
    deploy_robot(robot)
except DeploymentError as e:
    logger.error(f"Fallo deployment: {robot.name}", exc_info=True)
    # Manejar específicamente
except Exception as e:
    logger.critical(f"Error inesperado", exc_info=True)
    raise  # Re-lanzar para no ocultar
```

**Referencias:** [02_reglas_desarrollo.md](02_reglas_desarrollo.md#7-manejo-de-errores)

---

## 3. ANTIPATRONES DE CONFIGURACIÓN

### ❌ Hardcodear Credenciales

**Problema:**
```python
# MAL: Credenciales en código
API_KEY = "abc123xyz789"
DB_PASSWORD = "MiPassword123"
```

**Por qué es malo:**
- 🔴 **Seguridad**: Expuesto en repositorio
- 🔴 **Rotación**: Requiere cambiar código
- 🔴 **Ambientes**: Mismas credenciales dev/prod

**Solución:**
```python
# BIEN: Usar variables de entorno
import os
from sam.common.config_manager import ConfigManager

config = ConfigManager()
api_key = config.get("AA_CR_API_KEY")
db_password = os.getenv("SQL_SAM_PWD")
```

**Referencias:** [04_seguridad.md](04_seguridad.md#2-manejo-de-credenciales)

---

### ❌ Rutas Absolutas Hardcodeadas

**Problema:**
```python
# MAL: Ruta absoluta específica del servidor
log_file = "C:\\Proyectos\\SAM\\logs\\lanzador.log"
```

**Por qué es malo:**
- 🔴 **Portabilidad**: Solo funciona en un servidor
- 🔴 **Desarrollo**: No funciona en máquinas de devs
- 🔴 **Mantenimiento**: Cambiar ubicación requiere cambiar código

**Solución:**
```python
# BIEN: Rutas relativas con pathlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
log_file = PROJECT_ROOT / "logs" / "lanzador.log"

# O desde variable de entorno
log_dir = Path(os.getenv("SAM_LOG_DIR", "C:/RPA/Logs/SAM"))
log_file = log_dir / "lanzador.log"
```

**Referencias:** [02_reglas_desarrollo.md](02_reglas_desarrollo.md#8-infraestructura-windows)

---

### ❌ Configuración Mágica (Sin Documentar)

**Problema:**
```python
# MAL: Valores mágicos sin explicación
TIMEOUT = 42
MAX_RETRIES = 7
COOLDOWN_PERIOD = 300
```

**Por qué es malo:**
- 🔴 **Mantenimiento**: Nadie sabe por qué esos valores
- 🔴 **Tuning**: Difícil optimizar sin contexto
- 🔴 **Onboarding**: Nuevos devs confundidos

**Solución:**
```python
# BIEN: Constantes documentadas y configurables
# Timeout para API A360 (segundos)
# Valor basado en SLA de A360: 95% respuestas < 30s
API_TIMEOUT_SECONDS = int(os.getenv("AA_API_TIMEOUT_SECONDS", "30"))

# Reintentos para errores 412 temporales
# Basado en análisis: 90% se resuelven en 3 intentos
MAX_DEPLOYMENT_RETRIES = int(os.getenv("LANZADOR_MAX_REINTENTOS", "5"))

# Cooldown de pool (segundos) para evitar fluctuaciones
# Permite estabilizar antes de reasignar
POOL_COOLDOWN_SECONDS = int(os.getenv("BALANCEADOR_POOL_COOLDOWN_SEG", "300"))
```

**Referencias:** [02_reglas_desarrollo.md](02_reglas_desarrollo.md)

---

## 4. ANTIPATRONES DE OPERACIÓN

### ❌ Reiniciar Servicios Sin Verificar Impacto

**Problema:**
```powershell
# MAL: Reiniciar sin verificar estado
Restart-Service SAM_Lanzador
```

**Por qué es malo:**
- 🔴 **Pérdida de datos**: Ejecuciones en curso pueden perderse
- 🔴 **Cascada**: Puede afectar otros servicios
- 🔴 **Sin diagnóstico**: No se sabe qué causó el problema

**Solución:**
```powershell
# BIEN: Verificar antes de reiniciar
# 1. Verificar estado actual
Get-Service SAM_Lanzador | Format-List

# 2. Verificar ejecuciones en curso
sqlcmd -S [SERVER] -d SAM -Q "SELECT COUNT(*) FROM dbo.Ejecuciones WHERE Estado IN ('DEPLOYED', 'RUNNING')"

# 3. Revisar logs para entender el problema
Get-Content C:\RPA\Logs\SAM\lanzador.log -Tail 50

# 4. Si es seguro, reiniciar
Write-Host "⚠️ Reiniciando servicio SAM_Lanzador..."
Restart-Service SAM_Lanzador

# 5. Verificar que arrancó correctamente
Start-Sleep -Seconds 5
Get-Service SAM_Lanzador
```

**Referencias:** [06_troubleshooting.md](06_troubleshooting.md)

---

### ❌ Modificar BD en Producción Sin Backup

**Problema:**
```sql
-- MAL: UPDATE masivo sin backup
UPDATE dbo.Ejecuciones
SET Estado = 'COMPLETED'
WHERE Estado = 'UNKNOWN';
```

**Por qué es malo:**
- 🔴 **Irreversible**: No se puede deshacer
- 🔴 **Sin evidencia**: No hay registro del estado anterior
- 🔴 **Compliance**: Viola auditoría

**Solución:**
```sql
-- BIEN: Backup antes de modificar
-- 1. Crear tabla temporal con estado actual
SELECT *
INTO #Backup_Ejecuciones_UNKNOWN_20250119
FROM dbo.Ejecuciones
WHERE Estado = 'UNKNOWN';

-- 2. Verificar backup
SELECT COUNT(*) FROM #Backup_Ejecuciones_UNKNOWN_20250119;

-- 3. Realizar cambio
UPDATE dbo.Ejecuciones
SET Estado = 'COMPLETED', FechaFin = GETDATE()
WHERE Estado = 'UNKNOWN'
AND DATEDIFF(DAY, FechaUltimoUNKNOWN, GETDATE()) > 7;

-- 4. Verificar resultado
SELECT COUNT(*) FROM dbo.Ejecuciones WHERE Estado = 'COMPLETED_INFERRED';

-- 5. Si algo salió mal, restaurar
-- INSERT INTO dbo.Ejecuciones SELECT * FROM #Backup_Ejecuciones_UNKNOWN_20250119;
```

**Referencias:** [04_seguridad.md](04_seguridad.md#3-acceso-a-base-de-datos)

---

### ❌ Ignorar Alertas

**Problema:**
```
# MAL: Recibir alerta y no actuar
Email: "CRITICAL: 25 fallos 412 consecutivos en Equipo_5"
Acción: Ninguna (esperar que se resuelva solo)
```

**Por qué es malo:**
- 🔴 **Degradación**: Problema se agrava
- 🔴 **SLA**: Incumplimiento de tiempos
- 🔴 **Cascada**: Puede afectar otros robots

**Solución:**
```markdown
# BIEN: Protocolo de respuesta a alertas

1. **Reconocer**: Confirmar recepción (reply al email)
2. **Diagnosticar**: Seguir guía de troubleshooting
3. **Actuar**: Aplicar solución o escalar
4. **Documentar**: Registrar en ticket/wiki
5. **Prevenir**: Identificar causa raíz
```

**Referencias:** [06_troubleshooting.md](06_troubleshooting.md#escalamiento)

---

## 5. ANTIPATRONES DE SEGURIDAD

### ❌ Deshabilitar Verificación SSL

**Problema:**
```python
# MAL: Deshabilitar SSL en producción
import httpx
client = httpx.AsyncClient(verify=False)  # ❌ Vulnerable a MITM
```

**Por qué es malo:**
- 🔴 **Seguridad**: Vulnerable a ataques Man-in-the-Middle
- 🔴 **Compliance**: Viola políticas de seguridad
- 🔴 **Datos sensibles**: Credenciales expuestas

**Solución:**
```python
# BIEN: Siempre verificar SSL
import httpx
import os

# Permitir deshabilitar SOLO en desarrollo (documentado)
verify_ssl = os.getenv("AA_VERIFY_SSL", "true").lower() == "true"

if not verify_ssl:
    logger.warning("⚠️ SSL verification DISABLED - Solo para desarrollo")

client = httpx.AsyncClient(verify=verify_ssl)
```

**Referencias:** [04_seguridad.md](04_seguridad.md#7-comunicaciones-externas)

---

### ❌ Loguear Credenciales

**Problema:**
```python
# MAL: Logger exponiendo credenciales
logger.info(f"Conectando con usuario: {username}, password: {password}")
```

**Por qué es malo:**
- 🔴 **Exposición**: Credenciales en logs de texto plano
- 🔴 **Compliance**: Viola GDPR/PCI-DSS
- 🔴 **Auditoría**: Logs son accesibles por múltiples personas

**Solución:**
```python
# BIEN: Logger sin datos sensibles
logger.info(f"Conectando a base de datos como usuario: {username}")
logger.debug(f"Token: {token[:8]}***")  # Solo primeros caracteres
```

**Referencias:** [04_seguridad.md](04_seguridad.md#5-exposición-de-datos-sensibles)

---

### ❌ Permisos Excesivos en BD

**Problema:**
```sql
-- MAL: Usuario de aplicación con permisos de admin
GRANT db_owner TO SAM_AppUser;
```

**Por qué es malo:**
- 🔴 **Principio de mínimo privilegio**: Violado
- 🔴 **Riesgo**: Puede borrar tablas accidentalmente
- 🔴 **Auditoría**: Difícil rastrear cambios

**Solución:**
```sql
-- BIEN: Permisos granulares
-- Solo EXECUTE en Stored Procedures
GRANT EXECUTE ON SCHEMA::dbo TO SAM_AppUser;

-- SELECT solo en tablas necesarias
GRANT SELECT ON dbo.ConfiguracionSistema TO SAM_AppUser;

-- Denegar operaciones peligrosas
DENY DELETE, TRUNCATE, DROP ON SCHEMA::dbo TO SAM_AppUser;
```

**Referencias:** [04_seguridad.md](04_seguridad.md)

---

## 📋 CHECKLIST ANTI-ANTIPATRONES

Antes de hacer commit, verifica:

### Base de Datos
- [ ] ¿Usé Stored Procedures en lugar de SQL crudo?
- [ ] ¿Agregué TRY...CATCH a los SPs?
- [ ] ¿Registré cambios manuales en auditoría?

### Python
- [ ] ¿Usé `logger` en lugar de `print()`?
- [ ] ¿Agregué type hints a todas las funciones?
- [ ] ¿Usé `async/await` para operaciones I/O?
- [ ] ¿Capturé excepciones específicas?

### Configuración
- [ ] ¿Usé variables de entorno para credenciales?
- [ ] ¿Usé `pathlib.Path` en lugar de strings?
- [ ] ¿Documenté valores de configuración?

### Operación
- [ ] ¿Verifiqué impacto antes de reiniciar servicios?
- [ ] ¿Hice backup antes de modificar BD?
- [ ] ¿Respondí a alertas en tiempo razonable?

### Seguridad
- [ ] ¿Mantuve verificación SSL habilitada?
- [ ] ¿Evité loguear credenciales?
- [ ] ¿Usé permisos mínimos necesarios?

---

## 📚 REFERENCIAS

- [02_reglas_desarrollo.md](02_reglas_desarrollo.md) - Estándares de código
- [03_reglas_sql.md](03_reglas_sql.md) - Reglas de base de datos
- [04_seguridad.md](04_seguridad.md) - Políticas de seguridad
- [06_troubleshooting.md](06_troubleshooting.md) - Guía de diagnóstico

---

*Última revisión: 2025-01-19*
