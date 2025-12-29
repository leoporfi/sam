# Guía de Pruebas: Robots Cíclicos con Ventanas

## ✅ Estado Actual

### Backend Python
- ✅ `schemas.py` actualizado con nuevos campos (`EsCiclico`, `HoraFin`, `FechaInicioVentana`, `FechaFinVentana`, `IntervaloEntreEjecuciones`)
- ✅ `database.py` actualizado para pasar los nuevos parámetros a los SPs
- ✅ Funciones `create_schedule()`, `update_schedule()`, `update_schedule_simple()` listas

### Base de Datos
- ⚠️ **PENDIENTE**: Los SPs necesitan ser actualizados con los nuevos parámetros
  - `CrearProgramacion` - Falta actualizar
  - `ActualizarProgramacionCompleta` - Falta actualizar  
  - `ActualizarProgramacionSimple` - Falta actualizar

## 🔧 Pasos para Completar la Migración

### 1. Actualizar los Stored Procedures

Ejecutar en SQL Server Management Studio (en este orden):

```sql
-- Paso 1: Actualizar SPs principales
update_stored_procedures_ciclicos.sql

-- Paso 2: Actualizar SP simple
update_ActualizarProgramacionSimple.sql

-- Paso 3: Verificar que todo esté bien
verificar_backend_listo.sql
```

**IMPORTANTE**: Si `verificar_backend_listo.sql` muestra que faltan parámetros, significa que los scripts anteriores no se ejecutaron completamente. Revisar errores de sintaxis.

### 2. Probar la Funcionalidad

Una vez que los SPs estén actualizados, ejecutar:

```bash
python probar_ciclicos.py
```

Este script:
- ✅ Se conecta a la BD automáticamente
- ✅ Obtiene un RobotId y EquipoId válidos
- ✅ Crea una programación cíclica de prueba
- ✅ Verifica que los campos nuevos estén poblados
- ✅ Prueba retrocompatibilidad (programaciones tradicionales)

## 📋 Qué Prueba el Script

### Prueba 1: Programación Cíclica
- Crea una programación diaria cíclica
- Horario: 09:00:00 - 17:00:00
- Intervalo: 30 minutos
- Verifica que `EsCiclico=1`, `HoraFin`, `IntervaloEntreEjecuciones` estén poblados

### Prueba 2: Retrocompatibilidad
- Crea una programación tradicional (sin nuevos campos)
- Verifica que `EsCiclico` sea NULL o 0
- Confirma que las programaciones antiguas siguen funcionando

## 🚨 Solución de Problemas

### Error: "Faltan algunos parámetros" en verificar_backend_listo.sql

**Causa**: Los SPs no se actualizaron correctamente.

**Solución**:
1. Revisar si hubo errores al ejecutar `update_stored_procedures_ciclicos.sql`
2. Verificar que el script se ejecutó completamente (no se detuvo a mitad)
3. Si hay errores de sintaxis, corregirlos y volver a ejecutar

### Error: "No se pudo conectar a SQL Server"

**Causa**: La base de datos no está disponible o las variables de entorno no están configuradas.

**Solución**:
1. Verificar que SQL Server esté corriendo
2. Verificar variables de entorno:
   - `SQL_SAM_HOST`
   - `SQL_SAM_DB_NAME`
   - `SQL_SAM_UID`
   - `SQL_SAM_PWD`
3. O ejecutar el script desde el mismo servidor donde corre el servicio

### Error: "No hay robots activos en la BD"

**Causa**: No hay datos de prueba en la BD.

**Solución**: Crear al menos un robot y un equipo activos en la BD para pruebas.

## 📝 Ejemplo de Uso desde API

Una vez que todo esté funcionando, puedes crear programaciones cíclicas desde la API:

```python
import requests

# Programación cíclica diaria (9 AM - 5 PM, cada 30 min)
data = {
    "RobotId": 1,
    "TipoProgramacion": "Diaria",
    "HoraInicio": "09:00:00",
    "HoraFin": "17:00:00",
    "Tolerancia": 15,
    "Equipos": [1],
    "EsCiclico": True,
    "IntervaloEntreEjecuciones": 30
}

response = requests.post("http://localhost:8000/api/schedules", json=data)
```

## ✅ Checklist Final

- [ ] Ejecutar `update_stored_procedures_ciclicos.sql` completo
- [ ] Ejecutar `update_ActualizarProgramacionSimple.sql`
- [ ] Ejecutar `verificar_backend_listo.sql` y confirmar que todos los parámetros están presentes
- [ ] Ejecutar `probar_ciclicos.py` y confirmar que todas las pruebas pasan
- [ ] Probar crear una programación cíclica desde la API (opcional)

## 📞 Siguiente Paso

Una vez que los SPs estén actualizados y las pruebas pasen, la funcionalidad estará completamente lista para usar.

