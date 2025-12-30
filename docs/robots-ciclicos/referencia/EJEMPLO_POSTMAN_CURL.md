# Ejemplos de Prueba: Crear Programación Cíclica

## 📋 Prerequisitos

1. ✅ Ejecutar `update_ActualizarProgramacionSimple.sql` en la BD
2. ✅ Servicio web corriendo
3. ✅ Tener un `RobotId` y `EquipoId` válidos

## 🧪 Ejemplo 1: Programación Cíclica Simple

### cURL
```bash
curl -X POST "http://localhost:8000/api/schedules" \
  -H "Content-Type: application/json" \
  -d '{
    "RobotId": 1,
    "TipoProgramacion": "Diaria",
    "HoraInicio": "09:00:00",
    "HoraFin": "17:00:00",
    "Tolerancia": 15,
    "Equipos": [1],
    "EsCiclico": true,
    "IntervaloEntreEjecuciones": 30
  }'
```

### Postman
- **Method:** POST
- **URL:** `http://localhost:8000/api/schedules`
- **Headers:** `Content-Type: application/json`
- **Body (raw JSON):**
```json
{
  "RobotId": 1,
  "TipoProgramacion": "Diaria",
  "HoraInicio": "09:00:00",
  "HoraFin": "17:00:00",
  "Tolerancia": 15,
  "Equipos": [1],
  "EsCiclico": true,
  "IntervaloEntreEjecuciones": 30
}
```

## 🧪 Ejemplo 2: Programación Cíclica con Ventana de Fechas

### cURL
```bash
curl -X POST "http://localhost:8000/api/schedules" \
  -H "Content-Type: application/json" \
  -d '{
    "RobotId": 1,
    "TipoProgramacion": "Semanal",
    "DiasSemana": "Lun,Mar,Mie,Jue,Vie",
    "HoraInicio": "08:00:00",
    "HoraFin": "18:00:00",
    "Tolerancia": 10,
    "Equipos": [1],
    "EsCiclico": true,
    "FechaInicioVentana": "2025-01-01",
    "FechaFinVentana": "2025-12-31",
    "IntervaloEntreEjecuciones": 60
  }'
```

## 🧪 Ejemplo 3: Retrocompatibilidad (Sin Nuevos Campos)

### cURL
```bash
curl -X POST "http://localhost:8000/api/schedules" \
  -H "Content-Type: application/json" \
  -d '{
    "RobotId": 1,
    "TipoProgramacion": "Diaria",
    "HoraInicio": "10:00:00",
    "Tolerancia": 15,
    "Equipos": [1]
  }'
```

**Nota:** Este ejemplo NO incluye los nuevos campos. Debe funcionar igual que antes.

## ✅ Verificación en Base de Datos

Después de crear una programación, verificar en SQL:

```sql
SELECT
    ProgramacionId,
    RobotId,
    TipoProgramacion,
    HoraInicio,
    HoraFin,  -- Nuevo campo
    EsCiclico,  -- Nuevo campo
    FechaInicioVentana,  -- Nuevo campo
    FechaFinVentana,  -- Nuevo campo
    IntervaloEntreEjecuciones,  -- Nuevo campo
    Activo
FROM Programaciones
WHERE ProgramacionId = SCOPE_IDENTITY()  -- O usar el ID retornado
```

## 🔍 Verificar que se Ejecuta

1. Esperar al horario de ejecución
2. Verificar en `ObtenerRobotsEjecutables`:
```sql
EXEC dbo.ObtenerRobotsEjecutables;
```

3. Verificar en logs del Lanzador que el robot se ejecuta cíclicamente
