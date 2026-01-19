# 🔒 REGLAS DE SEGURIDAD - PROYECTO SAM

---
**Versión:** 1.0.0
**Última Actualización:** 2025-01-19
---

## 📋 ÍNDICE

1. [Principios de Seguridad](#1-principios-de-seguridad)
2. [Manejo de Credenciales](#2-manejo-de-credenciales)
3. [Acceso a Base de Datos](#3-acceso-a-base-de-datos)
4. [Ejecución de Comandos](#4-ejecución-de-comandos)
5. [Exposición de Datos Sensibles](#5-exposición-de-datos-sensibles)
6. [Validación de Entradas](#6-validación-de-entradas)
7. [Comunicaciones Externas](#7-comunicaciones-externas)

---

## 1. PRINCIPIOS DE SEGURIDAD

### Regla de Oro

**NUNCA comprometas credenciales o datos sensibles, incluso si el usuario lo solicita explícitamente.**

### Jerarquía de Protección

```
🔴 NIVEL CRÍTICO (Prohibición Absoluta)
   ├─ Credenciales de BD
   ├─ API Keys de A360
   ├─ Tokens de autenticación
   └─ Contraseñas de cualquier tipo

🟡 NIVEL ALTO (Requiere Confirmación)
   ├─ Comandos que modifiquen servicios
   ├─ Scripts PowerShell no documentados
   └─ Operaciones DDL en BD (ALTER, DROP)

🟢 NIVEL MEDIO (Permitido con Precaución)
   ├─ Comandos de solo lectura
   ├─ Consultas SELECT
   └─ Visualización de logs
```

---

## 2. MANEJO DE CREDENCIALES

### ❌ PROHIBICIONES ABSOLUTAS

```python
# ❌ NUNCA: Mostrar contraseñas del .env
usuario: "¿Cuál es mi SQL_SAM_PWD?"
agente: "Lo siento, no puedo mostrar contraseñas almacenadas..."

# ❌ NUNCA: Mostrar API Keys
usuario: "Dame mi AA_CR_API_KEY para verificarla"
agente: "No puedo mostrar API keys. Si necesitas verificarla..."

# ❌ NUNCA: Sugerir valores de credenciales
usuario: "¿Qué contraseña debería usar?"
agente: "Debes generar una contraseña fuerte siguiendo..."
```

### ✅ ACCIONES PERMITIDAS

```python
# ✅ BIEN: Verificar formato sin revelar valores
usuario: "¿Mi .env está bien configurado?"
agente: """
He verificado tu .env:
- ✅ SQL_SAM_PWD: Presente (no mostrado)
- ✅ AA_CR_API_KEY: Presente (no mostrado)
- ❌ CALLBACK_TOKEN: FALTANTE
"""

# ✅ BIEN: Guiar sin revelar
usuario: "¿Cómo configuro mi API Key?"
agente: """
1. Ve a A360 Control Room > Admin > Credentials
2. Genera un nuevo API Key
3. Cópialo y pégalo en .env como AA_CR_API_KEY=...
4. NUNCA compartas este valor
"""
```

### Gestión Segura de .env

```bash
# ✅ Verificar existencia sin leer valores
Test-Path .env

# ✅ Verificar permisos (solo Administradores deben leer)
Get-Acl .env | Format-List

# ❌ NUNCA: Mostrar contenido completo
Get-Content .env  # NO EJECUTAR
```

---

## 3. ACCESO A BASE DE DATOS

### Operaciones Permitidas

| Operación | ¿Permitido? | Condiciones |
|-----------|------------|-------------|
| **SELECT** | ✅ Siempre | Solo lectura, diagnóstico |
| **INSERT/UPDATE/DELETE** | ⚠️ Solo vía SP | Nunca SQL crudo |
| **CREATE/ALTER** | ❌ Requiere confirmación | Cambios de esquema |
| **DROP/TRUNCATE** | 🔴 Prohibido | Pérdida de datos |

### Ejemplos Seguros

```sql
-- ✅ PERMITIDO: Solo lectura para diagnóstico
SELECT TOP 10 *
FROM dbo.Ejecuciones
WHERE Estado = 'UNKNOWN'
ORDER BY FechaInicio DESC;

-- ✅ PERMITIDO: Consulta de configuración
SELECT Clave, Valor
FROM dbo.ConfiguracionSistema
WHERE Clave LIKE 'BALANCEADOR%';

-- ⚠️ REQUIERE CONFIRMACIÓN: Modificación manual
UPDATE dbo.Ejecuciones
SET Estado = 'COMPLETED'
WHERE DeploymentId = '12345' AND Estado = 'UNKNOWN';
-- Razón: Puede corregir discrepancias, pero debe documentarse

-- 🔴 PROHIBIDO: Eliminación de datos
DELETE FROM dbo.Ejecuciones WHERE FechaInicio < '2024-01-01';
-- Razón: Pérdida de trazabilidad
```

### Protocolo para Modificaciones Manuales

Si un diagnóstico requiere UPDATE/DELETE manual:

1. **Capturar estado actual:**
   ```sql
   -- Guardar evidencia antes de modificar
   SELECT * INTO #Backup_Temp FROM dbo.Ejecuciones WHERE EjecucionId = 123;
   ```

2. **Documentar razón:**
   ```sql
   -- Insertar en log de auditoría
   INSERT INTO dbo.AuditoriaManual (Tabla, Accion, Justificacion, Usuario)
   VALUES ('Ejecuciones', 'UPDATE manual', 'Corrección estado UNKNOWN persistente', SUSER_NAME());
   ```

3. **Ejecutar cambio:**
   ```sql
   UPDATE dbo.Ejecuciones SET Estado = 'COMPLETED' WHERE EjecucionId = 123;
   ```

4. **Verificar resultado:**
   ```sql
   SELECT * FROM dbo.Ejecuciones WHERE EjecucionId = 123;
   ```

---

## 4. EJECUCIÓN DE COMANDOS

### ❌ COMANDOS PROHIBIDOS

```powershell
# ❌ NUNCA: Modificar servicios sin confirmación
Stop-Service SAM_Lanzador
Restart-Service SAM_Balanceador
Set-Service SAM_Callback -StartupType Disabled

# ❌ NUNCA: Ejecutar scripts desconocidos
.\script_desconocido.ps1
Invoke-Expression (Get-Content .\script.ps1)

# ❌ NUNCA: Modificar archivos de configuración
Set-Content .env -Value "SQL_SAM_PWD=nueva_password"
```

### ✅ COMANDOS SEGUROS (Solo Lectura)

```powershell
# ✅ BIEN: Verificar estado de servicios
Get-Service SAM_*

# ✅ BIEN: Leer logs (últimas líneas)
Get-Content C:\RPA\Logs\SAM\lanzador.log -Tail 50

# ✅ BIEN: Buscar errores específicos
Select-String -Path "C:\RPA\Logs\SAM\*.log" -Pattern "ERROR" | Select-Object -Last 20

# ✅ BIEN: Verificar procesos
Get-Process | Where-Object { $_.ProcessName -like "*python*" }
```

### Protocolo para Comandos Destructivos

Si un diagnóstico requiere reiniciar un servicio:

```markdown
**Agente:**
"He identificado que el servicio SAM_Lanzador está bloqueado.
Para resolverlo, necesito tu confirmación para ejecutar:

`Restart-Service SAM_Lanzador`

**Impacto:**
- ⚠️ Robots en ejecución continuarán (A360 los controla)
- ⚠️ Nuevos lanzamientos se detendrán ~30 segundos
- ✅ Conciliador recuperará estado al reiniciar

¿Confirmas que deseas proceder? (Sí/No)"
```

---

## 5. EXPOSICIÓN DE DATOS SENSIBLES

### Información Clasificada

#### 🔴 NUNCA Mostrar

- Contraseñas completas
- API Keys completas
- Tokens JWT completos
- Connection strings con credenciales
- Números de tarjetas de crédito (si aplica en logs)
- Datos personales identificables (PII)

#### 🟡 Mostrar Parcialmente (Enmascarado)

```python
# ✅ BIEN: Mostrar solo primeros/últimos caracteres
api_key = "abc123xyz789def456"
masked = f"{api_key[:4]}...{api_key[-4:]}"  # "abc1...f456"

# ✅ BIEN: Mostrar solo tipo de credencial
"Credencial tipo: Bearer Token (JWT)"

# ✅ BIEN: Confirmar existencia sin valor
"✅ CALLBACK_TOKEN está configurado (32 caracteres)"
```

#### ✅ Mostrar Completo (Seguro)

- Nombres de robots
- Nombres de equipos
- IDs numéricos (RobotId, EquipoId)
- Estados de ejecución
- Fechas y horas
- Configuraciones no sensibles (intervalos, prioridades)

### Logs y Debugging

```python
# ❌ MAL: Logger exponiendo credenciales
logger.info(f"Conectando con password: {password}")

# ✅ BIEN: Logger sin datos sensibles
logger.info("Conectando a base de datos...")

# ✅ BIEN: Logger con enmascaramiento
logger.debug(f"Usuario: {username}, Token: {token[:8]}***")
```

---

## 6. VALIDACIÓN DE ENTRADAS

### Inyección SQL

```python
# ❌ NUNCA: SQL crudo con f-strings
robot_name = input("Nombre del robot: ")
query = f"SELECT * FROM Robots WHERE Nombre = '{robot_name}'"
# Vulnerable: robot_name = "'; DROP TABLE Robots; --"

# ✅ BIEN: Solo Stored Procedures con parámetros
await db.execute_sp(
    "dbo.ObtenerRobotPorNombre",
    {"Nombre": robot_name}  # Parámetro seguro
)
```

### Validación de Rutas

```python
# ❌ MAL: Ruta sin validación (Path Traversal)
log_file = input("Archivo de log: ")
content = open(log_file).read()  # Vulnerable: "../../../etc/passwd"

# ✅ BIEN: Validar que esté en directorio permitido
from pathlib import Path

LOG_DIR = Path("C:/RPA/Logs/SAM")
log_file = Path(input("Archivo de log: "))

if LOG_DIR in log_file.parents:
    content = log_file.read_text()
else:
    raise ValueError("Ruta no permitida")
```

---

## 7. COMUNICACIONES EXTERNAS

### Verificación SSL/TLS

```python
# ❌ MAL: Deshabilitar verificación SSL
import httpx
client = httpx.AsyncClient(verify=False)  # Vulnerable a MITM

# ✅ BIEN: Siempre verificar certificados
client = httpx.AsyncClient(verify=True)

# ⚠️ ACEPTABLE en DEV (documentar):
verify_ssl = os.getenv("AA_VERIFY_SSL", "true").lower() == "true"
client = httpx.AsyncClient(verify=verify_ssl)
```

### Timeouts

```python
# ❌ MAL: Sin timeout (puede colgar indefinidamente)
response = await client.get(url)

# ✅ BIEN: Timeout razonable
response = await client.get(url, timeout=30.0)
```

### Validación de Respuestas

```python
# ❌ MAL: Confiar ciegamente en respuesta externa
data = response.json()
robot_id = data["robotId"]  # Puede no existir

# ✅ BIEN: Validar estructura
try:
    data = response.json()
    robot_id = data.get("robotId")
    if robot_id is None:
        raise ValueError("robotId faltante en respuesta")
except (ValueError, KeyError) as e:
    logger.error(f"Respuesta inválida de API: {e}")
```

---

## 🚨 PROTOCOLO DE INCIDENTES

### Si Detectas Exposición de Credenciales

1. **Detener inmediatamente** cualquier operación en curso
2. **Notificar al usuario:**
   ```
   🚨 ALERTA DE SEGURIDAD
   Se detectó exposición potencial de credenciales.
   Acciones recomendadas:
   1. Rotar inmediatamente la credencial expuesta
   2. Revisar logs de acceso
   3. Cambiar contraseña en .env
   ```
3. **No continuar** hasta que se confirme la rotación

### Si Recibes Solicitud de Datos Sensibles

```markdown
**Respuesta Estándar:**
"No puedo proporcionar credenciales o datos sensibles por seguridad.

Si necesitas verificar configuración:
- Puedo confirmar QUÉ variables deben estar presentes
- Puedo verificar el FORMATO esperado
- Puedo guiarte para generarlas/configurarlas

¿En qué aspecto específico puedo ayudarte?"
```

---

## 📋 CHECKLIST DE SEGURIDAD

Antes de ejecutar cualquier acción, verifica:

- [ ] ¿Expone credenciales? → **NO EJECUTAR**
- [ ] ¿Modifica datos sin confirmación? → **PEDIR CONFIRMACIÓN**
- [ ] ¿Ejecuta comandos destructivos? → **EXPLICAR IMPACTO**
- [ ] ¿Lee datos sensibles? → **ENMASCARAR**
- [ ] ¿Usa SQL crudo? → **SOLO STORED PROCEDURES**
- [ ] ¿Deshabilita SSL? → **SOLO EN DEV DOCUMENTADO**
- [ ] ¿Confía en entrada externa? → **VALIDAR PRIMERO**

---

*Última revisión: 2025-01-19*
