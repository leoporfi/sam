# Feature: Robots Cíclicos con Ventanas Temporales

## 📋 Resumen

Esta feature permite que robots programados se ejecuten **cíclicamente** (repetidamente) pero solo dentro de **ventanas temporales** definidas (rangos horarios y fechas).

### Problema Resuelto

**Antes:**
- Robots **Online** (`EsOnline = 1`): Se ejecutan cíclicamente sin restricciones temporales
- Robots **Programados**: Se ejecutan una sola vez según cronograma, con restricciones temporales

**Ahora:**
- Robots **Cíclicos con Ventanas**: Se ejecutan repetidamente pero solo dentro de ventanas temporales definidas

## 🗂️ Archivos Creados/Modificados

### Scripts SQL

1. **`migration_robots_ciclicos_ventanas.sql`**
   - Agrega campos a la tabla `Programaciones`
   - Crea el SP `ValidarSolapamientoVentanas`

2. **`update_stored_procedures_ciclicos.sql`**
   - Modifica `CrearProgramacion` (nuevos parámetros + validación de solapamientos)
   - Modifica `ObtenerRobotsEjecutables` (lógica para robots cíclicos)
   - Modifica `ActualizarProgramacionCompleta` (nuevos parámetros + validación)

## 📊 Cambios en el Modelo de Datos

### Tabla `Programaciones` - Nuevos Campos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `EsCiclico` | `bit` | Indica si el robot se ejecuta cíclicamente (1) o solo una vez (0/NULL) |
| `HoraFin` | `time(0)` | Hora de fin del rango horario permitido. NULL = todo el día |
| `FechaInicioVentana` | `date` | Fecha desde la cual la ventana es válida. NULL = desde creación |
| `FechaFinVentana` | `date` | Fecha hasta la cual la ventana es válida. NULL = indefinidamente |
| `IntervaloEntreEjecuciones` | `int` | Minutos de espera entre ejecuciones cíclicas. NULL = tan pronto como esté disponible |

## 🔧 Stored Procedures Modificados

### 1. `CrearProgramacion`

**Nuevos Parámetros:**
- `@EsCiclico BIT = 0`
- `@HoraFin TIME = NULL`
- `@FechaInicioVentana DATE = NULL`
- `@FechaFinVentana DATE = NULL`
- `@IntervaloEntreEjecuciones INT = NULL`

**Nuevas Funcionalidades:**
- Validación de solapamientos de ventanas temporales
- Validación de rangos horarios y fechas
- Bloqueo de creación si hay conflictos

### 2. `ObtenerRobotsEjecutables`

**Cambios:**
- Separación entre robots programados tradicionales (una vez) y cíclicos
- Validación de ventanas temporales para robots cíclicos
- Respeto de `IntervaloEntreEjecuciones`
- Resolución de conflictos usando `PrioridadBalanceo` del robot

**Lógica de Ejecución:**
1. **Robots Programados Tradicionales**: Se ejecutan una vez cuando corresponde según cronograma
2. **Robots Cíclicos**: Se ejecutan repetidamente dentro de la ventana, respetando el intervalo
3. **Robots Online**: Sin cambios (ejecución continua)

### 3. `ActualizarProgramacionCompleta`

**Nuevos Parámetros:**
- `@EsCiclico BIT = NULL`
- `@HoraFin TIME = NULL`
- `@FechaInicioVentana DATE = NULL`
- `@FechaFinVentana DATE = NULL`
- `@IntervaloEntreEjecuciones INT = NULL`

**Nuevas Funcionalidades:**
- Validación de solapamientos al actualizar
- Actualización de campos cíclicos

### 4. `ValidarSolapamientoVentanas` (NUEVO)

**Propósito:**
Detecta solapamientos de ventanas temporales entre programaciones del mismo equipo.

**Parámetros:**
- `@EquipoId INT`
- `@HoraInicio TIME`
- `@HoraFin TIME = NULL`
- `@FechaInicioVentana DATE = NULL`
- `@FechaFinVentana DATE = NULL`
- `@DiasSemana NVARCHAR(20) = NULL`
- `@TipoProgramacion NVARCHAR(20)`
- `@DiaDelMes INT = NULL`
- `@DiaInicioMes INT = NULL`
- `@DiaFinMes INT = NULL`
- `@UltimosDiasMes INT = NULL`
- `@ProgramacionId INT = NULL` (para excluir en actualizaciones)

**Retorna:**
Lista de programaciones que se solapan con la propuesta.

## 🚀 Instrucciones de Instalación

### Paso 1: Ejecutar Migración de Tabla

```sql
-- Ejecutar en orden:
USE [SAM]
GO

-- 1. Agregar campos a Programaciones
EXEC migration_robots_ciclicos_ventanas.sql
```

### Paso 2: Actualizar Stored Procedures

```sql
-- 2. Actualizar SPs existentes
EXEC update_stored_procedures_ciclicos.sql
```

### Paso 3: Verificar

```sql
-- Verificar que los campos se agregaron correctamente
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'Programaciones'
  AND COLUMN_NAME IN ('EsCiclico', 'HoraFin', 'FechaInicioVentana', 'FechaFinVentana', 'IntervaloEntreEjecuciones');

-- Verificar que los SPs se actualizaron
SELECT name, create_date, modify_date
FROM sys.procedures
WHERE name IN ('CrearProgramacion', 'ObtenerRobotsEjecutables', 'ActualizarProgramacionCompleta', 'ValidarSolapamientoVentanas');
```

## 📝 Ejemplos de Uso

### Ejemplo 1: Robot Cíclico con Rango Horario

```sql
EXEC dbo.CrearProgramacion
    @Robot = 'Robot_Procesamiento',
    @Equipos = 'Equipo001,Equipo002',
    @TipoProgramacion = 'Diaria',
    @HoraInicio = '09:00:00',
    @HoraFin = '17:00:00',  -- Solo entre 9 AM y 5 PM
    @Tolerancia = 15,
    @EsCiclico = 1,
    @IntervaloEntreEjecuciones = 30;  -- Cada 30 minutos
```

### Ejemplo 2: Robot Cíclico con Ventana de Fechas

```sql
EXEC dbo.CrearProgramacion
    @Robot = 'Robot_Reporte',
    @Equipos = 'Equipo003',
    @TipoProgramacion = 'Semanal',
    @DiasSemana = 'Lun,Mar,Mie,Jue,Vie',
    @HoraInicio = '08:00:00',
    @HoraFin = '18:00:00',
    @Tolerancia = 10,
    @EsCiclico = 1,
    @FechaInicioVentana = '2025-01-01',  -- Desde el 1 de enero
    @FechaFinVentana = '2025-12-31',     -- Hasta el 31 de diciembre
    @IntervaloEntreEjecuciones = 60;      -- Cada hora
```

### Ejemplo 3: Robot Cíclico Todo el Día

```sql
EXEC dbo.CrearProgramacion
    @Robot = 'Robot_Monitoreo',
    @Equipos = 'Equipo004',
    @TipoProgramacion = 'Diaria',
    @HoraInicio = '00:00:00',
    @HoraFin = NULL,  -- Todo el día
    @Tolerancia = 5,
    @EsCiclico = 1,
    @IntervaloEntreEjecuciones = 15;  -- Cada 15 minutos
```

## ⚠️ Notas Importantes

### Validación de Solapamientos

- El sistema **bloquea** la creación de programaciones si hay solapamientos totales
- Se valida tanto el rango horario como las fechas y el tipo de programación
- Los robots cíclicos se tratan como asignaciones fijas (`EsProgramado = 1`), el Balanceador no los toca

### Prioridad de Ejecución

- En caso de conflicto (mismo equipo, misma hora), se usa `PrioridadBalanceo` del robot
- Menor número = mayor prioridad (1 > 10)
- Si hay empate, se ejecuta el que empezó primero

### Intervalo Entre Ejecuciones

- Si `IntervaloEntreEjecuciones` es NULL, el robot se ejecuta tan pronto como el equipo esté disponible
- Si está definido, se respeta el intervalo desde la última ejecución completada
- El intervalo se mide desde `FechaFin` de la ejecución anterior

## 🔄 Próximos Pasos (Pendientes)

1. **SPs de Carga**: Los SPs `CargarProgramacionDiaria`, `CargarProgramacionSemanal`, etc. pueden necesitar actualización si se usan desde el frontend
2. **Frontend**: Actualizar la interfaz web para permitir configurar robots cíclicos
3. **Backend Python**: Actualizar `database.py` para pasar los nuevos parámetros
4. **Documentación**: Actualizar documentación del modelo de datos

## 🐛 Troubleshooting

### Error: "Se detectaron solapamientos de ventanas temporales"

**Causa:** Hay otra programación activa en el mismo equipo con ventanas que se solapan.

**Solución:**
1. Revisar las programaciones existentes del equipo
2. Ajustar las ventanas horarias o fechas
3. Usar un equipo diferente

### Error: "HoraFin debe ser mayor que HoraInicio"

**Causa:** El rango horario es inválido.

**Solución:** Asegurar que `HoraFin > HoraInicio` (o NULL para todo el día)

### El robot cíclico no se ejecuta

**Verificar:**
1. `EsCiclico = 1` en la programación
2. La fecha/hora actual está dentro de la ventana
3. El equipo no está ocupado
4. Se respeta el `IntervaloEntreEjecuciones` (si está definido)

## 📚 Referencias

- Documentación del modelo de datos: `docs/Documentación del Modelo de Datos y Reglas de Negocio.md`
- Stored Procedures: `SAM.sql`
