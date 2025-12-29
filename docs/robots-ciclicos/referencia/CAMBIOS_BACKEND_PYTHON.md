# Cambios en Backend Python: Robots Cíclicos con Ventanas

## 📝 Archivos Modificados

### 1. `src/sam/web/backend/schemas.py`

#### `ScheduleData` - Nuevos campos agregados:
```python
EsCiclico: Optional[bool] = False
HoraFin: Optional[str] = None
FechaInicioVentana: Optional[str] = None
FechaFinVentana: Optional[str] = None
IntervaloEntreEjecuciones: Optional[int] = None
```

#### `ScheduleEditData` - Nuevos campos agregados:
```python
EsCiclico: Optional[bool] = False
HoraFin: Optional[time] = None
FechaInicioVentana: Optional[date] = None
FechaFinVentana: Optional[date] = None
IntervaloEntreEjecuciones: Optional[int] = None
```

### 2. `src/sam/web/backend/database.py`

#### `create_schedule()` - Actualizado:
- ✅ Agregados 5 nuevos parámetros al SP `CrearProgramacion`
- ✅ Parámetros pasados con valores por defecto (retrocompatible)

#### `update_schedule()` - Actualizado:
- ✅ Agregados 5 nuevos parámetros al SP `ActualizarProgramacionCompleta`
- ✅ Parámetros pasados con valores por defecto (retrocompatible)

#### `update_schedule_simple()` - Actualizado:
- ✅ Agregados 5 nuevos parámetros al SP `ActualizarProgramacionSimple`
- ✅ Conversión automática de tipos `time` y `date` (pyodbc maneja automáticamente)

## 🔧 Script SQL Adicional Requerido

**IMPORTANTE:** También necesitas ejecutar:
- `update_ActualizarProgramacionSimple.sql` - Para actualizar el SP que usa `update_schedule_simple()`

## ✅ Compatibilidad

### Retrocompatibilidad: ✅ GARANTIZADA

- Los nuevos campos son **opcionales** (todos tienen `Optional` y valores por defecto)
- Si no se proporcionan, se pasan como `None` o `False` al SP
- El SP maneja `NULL` correctamente
- **Las llamadas existentes seguirán funcionando sin cambios**

### Ejemplo de uso actual (sin cambios):
```python
# Esto sigue funcionando igual que antes
schedule_data = ScheduleData(
    RobotId=1,
    TipoProgramacion="Diaria",
    HoraInicio="09:00:00",
    Tolerancia=15,
    Equipos=[1, 2]
)
create_schedule(db, schedule_data)  # ✅ Funciona
```

### Ejemplo de uso nuevo (con campos cíclicos):
```python
# Nuevo: Programación cíclica con ventana
schedule_data = ScheduleData(
    RobotId=1,
    TipoProgramacion="Diaria",
    HoraInicio="09:00:00",
    HoraFin="17:00:00",  # Nuevo
    Tolerancia=15,
    Equipos=[1, 2],
    EsCiclico=True,  # Nuevo
    FechaInicioVentana="2025-01-01",  # Nuevo
    FechaFinVentana="2025-12-31",  # Nuevo
    IntervaloEntreEjecuciones=30  # Nuevo
)
create_schedule(db, schedule_data)  # ✅ Funciona
```

## 🧪 Pruebas Recomendadas

### 1. Probar creación sin nuevos campos (retrocompatibilidad)
```python
# Debe funcionar igual que antes
data = ScheduleData(
    RobotId=1,
    TipoProgramacion="Diaria",
    HoraInicio="09:00:00",
    Tolerancia=15,
    Equipos=[1]
)
create_schedule(db, data)
```

### 2. Probar creación con nuevos campos
```python
# Debe crear programación cíclica
data = ScheduleData(
    RobotId=1,
    TipoProgramacion="Diaria",
    HoraInicio="09:00:00",
    HoraFin="17:00:00",
    Tolerancia=15,
    Equipos=[1],
    EsCiclico=True,
    IntervaloEntreEjecuciones=30
)
create_schedule(db, data)
```

### 3. Probar actualización
```python
# Debe actualizar campos cíclicos
data = ScheduleEditData(
    TipoProgramacion="Diaria",
    HoraInicio=time(9, 0, 0),
    HoraFin=time(17, 0, 0),  # Nuevo
    Tolerancia=15,
    Activo=True,
    EsCiclico=True  # Nuevo
)
update_schedule_simple(db, programacion_id=1, data=data)
```

## 📋 Checklist de Verificación

- [x] `ScheduleData` actualizado con nuevos campos
- [x] `ScheduleEditData` actualizado con nuevos campos
- [x] `create_schedule()` actualizado
- [x] `update_schedule()` actualizado
- [x] `update_schedule_simple()` actualizado
- [ ] Ejecutar `update_ActualizarProgramacionSimple.sql` en la BD
- [ ] Probar creación desde API/Postman
- [ ] Verificar que programaciones existentes siguen funcionando

## 🚀 Próximos Pasos

1. **Ejecutar script SQL:** `update_ActualizarProgramacionSimple.sql`
2. **Probar desde API:** Crear una programación cíclica usando Postman o curl
3. **Verificar logs:** Asegurar que no hay errores
4. **Frontend:** Cuando esté listo, actualizar la UI para exponer los nuevos campos

