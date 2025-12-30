# Pendientes: Frontend para Robots Cíclicos

## 📋 Resumen

El backend y la base de datos están completos y funcionando. **Falta actualizar el frontend** para permitir a los usuarios crear y editar programaciones cíclicas con ventanas temporales desde la interfaz web.

## ✅ Completado

- ✅ Base de datos: Columnas agregadas a `Programaciones`
- ✅ Stored Procedures: Actualizados y funcionando
- ✅ Backend Python: Schemas y database.py actualizados
- ✅ API: Endpoints funcionando correctamente
- ✅ Validaciones SQL: Implementadas
- ✅ Scripts de prueba: Funcionando

## ❌ Pendiente: Frontend

### 1. Formulario de Creación (`schedule_create_modal.py`)

**Archivo**: `src/sam/web/frontend/features/modals/schedule_create_modal.py`

**Campos a agregar en `ScheduleCreateForm`**:
- [ ] **EsCiclico**: Checkbox para activar modo cíclico
- [ ] **HoraFin**: Input tipo `time` (visible solo si `EsCiclico = True`)
- [ ] **FechaInicioVentana**: Input tipo `date` (visible solo si `EsCiclico = True`)
- [ ] **FechaFinVentana**: Input tipo `date` (visible solo si `EsCiclico = True`)
- [ ] **IntervaloEntreEjecuciones**: Input tipo `number` en minutos (visible solo si `EsCiclico = True`)

**Ubicación sugerida**: Después del campo "Tolerancia" y antes de "Equipos"

**Estado inicial en `ScheduleCreateModal`**:
```python
form_data, set_form_data = use_state({
    # ... campos existentes ...
    "EsCiclico": False,
    "HoraFin": None,
    "FechaInicioVentana": None,
    "FechaFinVentana": None,
    "IntervaloEntreEjecuciones": None,
})
```

### 2. Formulario de Edición (`schedule_modal.py`)

**Archivo**: `src/sam/web/frontend/features/modals/schedule_modal.py`

**Campos a agregar en `FullScheduleEditForm`**:
- [ ] **EsCiclico**: Checkbox para activar modo cíclico
- [ ] **HoraFin**: Input tipo `time` (visible solo si `EsCiclico = True`)
- [ ] **FechaInicioVentana**: Input tipo `date` (visible solo si `EsCiclico = True`)
- [ ] **FechaFinVentana**: Input tipo `date` (visible solo si `EsCiclico = True`)
- [ ] **IntervaloEntreEjecuciones**: Input tipo `number` en minutos (visible solo si `EsCiclico = True`)

**Ubicación sugerida**: Después del campo "Tolerancia" y antes del toggle "Activo"

**Sincronización en `ScheduleEditModal`**:
- Asegurar que los campos se carguen desde `schedule` cuando se abre el modal
- Formatear `HoraFin` de `time` a string "HH:MM" si viene de la BD

### 3. Formulario en Robots Modals (`robots_modals.py`)

**Archivo**: `src/sam/web/frontend/features/modals/robots_modals.py`

**Campos a agregar en `ScheduleForm`**:
- [ ] **EsCiclico**: Checkbox
- [ ] **HoraFin**: Input tipo `time`
- [ ] **FechaInicioVentana**: Input tipo `date`
- [ ] **FechaFinVentana**: Input tipo `date`
- [ ] **IntervaloEntreEjecuciones**: Input tipo `number`

**Estado inicial en `SchedulesModal`**:
```python
DEFAULT_FORM_STATE = {
    # ... campos existentes ...
    "EsCiclico": False,
    "HoraFin": None,
    "FechaInicioVentana": None,
    "FechaFinVentana": None,
    "IntervaloEntreEjecuciones": None,
}
```

**En `handle_edit_click`**:
```python
form_state = {
    # ... campos existentes ...
    "EsCiclico": schedule_to_edit.get("EsCiclico", False),
    "HoraFin": (schedule_to_edit.get("HoraFin") or "")[:5] if schedule_to_edit.get("HoraFin") else None,
    "FechaInicioVentana": schedule_to_edit.get("FechaInicioVentana"),
    "FechaFinVentana": schedule_to_edit.get("FechaFinVentana"),
    "IntervaloEntreEjecuciones": schedule_to_edit.get("IntervaloEntreEjecuciones"),
}
```

### 4. Visualización en Listas (`schedule_list.py`)

**Archivo**: `src/sam/web/frontend/features/components/schedule_list.py`

**Actualizar `ScheduleCard`**:
- [ ] Mostrar badge/etiqueta "Cíclico" si `EsCiclico = True`
- [ ] Mostrar rango horario: "09:00 - 17:00" si hay `HoraFin`
- [ ] Mostrar ventana de fechas: "01/01/2025 - 31/12/2025" si hay fechas
- [ ] Mostrar intervalo: "Cada 30 min" si hay `IntervaloEntreEjecuciones`

**Actualizar `SchedulesTable`**:
- [ ] Agregar columna "Tipo" que muestre "Cíclico" o "Programado"
- [ ] Mostrar rango horario en columna "Hora" si es cíclico
- [ ] Mostrar información de ventana en tooltip o columna adicional

**Actualizar función `format_schedule_details`** (en `shared/formatters.py`):
- [ ] Incluir información de robots cíclicos en el formato

### 5. Validaciones Frontend

**Agregar validaciones en todos los formularios**:

```python
# En handle_confirm_save o handle_submit:

# Validaciones para robots cíclicos
if form_data.get("EsCiclico"):
    if not form_data.get("HoraFin"):
        raise ValueError("Para robots cíclicos, la hora de fin es obligatoria.")

    hora_inicio = form_data.get("HoraInicio", "00:00")
    hora_fin = form_data.get("HoraFin")
    if hora_fin <= hora_inicio:
        raise ValueError("La hora de fin debe ser mayor que la hora de inicio.")

    fecha_inicio = form_data.get("FechaInicioVentana")
    fecha_fin = form_data.get("FechaFinVentana")
    if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
        raise ValueError("La fecha de inicio de ventana debe ser menor o igual a la fecha de fin.")

    if not form_data.get("IntervaloEntreEjecuciones"):
        raise ValueError("Para robots cíclicos, el intervalo entre ejecuciones es obligatorio.")

    intervalo = form_data.get("IntervaloEntreEjecuciones")
    if intervalo and intervalo < 1:
        raise ValueError("El intervalo entre ejecuciones debe ser al menos 1 minuto.")
```

### 6. Limpieza de Campos

**En `handle_change` de todos los formularios**:

```python
if field == "EsCiclico" and not value:
    # Si se desactiva EsCiclico, limpiar campos relacionados
    new_form_data["HoraFin"] = None
    new_form_data["FechaInicioVentana"] = None
    new_form_data["FechaFinVentana"] = None
    new_form_data["IntervaloEntreEjecuciones"] = None
```

## 🎨 Diseño Sugerido

### Sección de Campos Cíclicos

```html
<!-- Checkbox para activar modo cíclico -->
html.label(
    html.input({
        "type": "checkbox",
        "role": "switch",
        "checked": form_data.get("EsCiclico", False),
        "on_change": lambda e: handle_change("EsCiclico", e["target"]["checked"]),
    }),
    " Robot Cíclico (ejecución continua dentro de ventana)",
),

<!-- Campos condicionales (solo si EsCiclico = True) -->
html.div(
    {"style": {"display": "block" if form_data.get("EsCiclico") else "none"}},
    html.div(
        {"class_name": "grid"},
        html.label(
            "Hora de Fin (HH:MM) *",
            html.input({
                "type": "time",
                "value": form_data.get("HoraFin") or "",
                "on_change": lambda e: handle_change("HoraFin", e["target"]["value"]),
                "required": form_data.get("EsCiclico", False),
            }),
        ),
        html.label(
            "Intervalo entre Ejecuciones (minutos) *",
            html.input({
                "type": "number",
                "value": form_data.get("IntervaloEntreEjecuciones") or "",
                "min": 1,
                "max": 1440,
                "on_change": lambda e: handle_change("IntervaloEntreEjecuciones", int(e["target"]["value"]) if e["target"]["value"] else None),
                "required": form_data.get("EsCiclico", False),
            }),
        ),
    ),
    html.div(
        {"class_name": "grid"},
        html.label(
            "Fecha Inicio Ventana",
            html.input({
                "type": "date",
                "value": form_data.get("FechaInicioVentana") or "",
                "on_change": lambda e: handle_change("FechaInicioVentana", e["target"]["value"]),
            }),
        ),
        html.label(
            "Fecha Fin Ventana",
            html.input({
                "type": "date",
                "value": form_data.get("FechaFinVentana") or "",
                "on_change": lambda e: handle_change("FechaFinVentana", e["target"]["value"]),
            }),
        ),
    ),
    html.small(
        {"style": {"color": "var(--pico-muted-color)", "fontSize": "0.85em"}},
        "💡 Los robots cíclicos se ejecutan continuamente dentro del rango horario y ventana de fechas especificados.",
    ),
)
```

## 📝 Notas Importantes

1. **Retrocompatibilidad**: Los campos deben ser opcionales. Si `EsCiclico = False` o `NULL`, la programación funciona como antes.

2. **Formato de datos**:
   - `HoraFin`: String "HH:MM" (ej: "17:00")
   - `FechaInicioVentana`: String "YYYY-MM-DD" (ej: "2025-01-01")
   - `FechaFinVentana`: String "YYYY-MM-DD" (ej: "2025-12-31")
   - `IntervaloEntreEjecuciones`: Integer (minutos)

3. **Validaciones del backend**: El backend ya valida estos campos, pero es mejor validar también en frontend para mejor UX.

4. **Visualización**: Considerar agregar iconos o colores diferentes para distinguir programaciones cíclicas de las tradicionales.

## 🚀 Orden de Implementación Recomendado

1. **Formulario de creación** (`schedule_create_modal.py`) - Prioridad ALTA
2. **Formulario de edición** (`schedule_modal.py`) - Prioridad ALTA
3. **Visualización en listas** (`schedule_list.py`) - Prioridad MEDIA
4. **Formulario en robots modals** (`robots_modals.py`) - Prioridad MEDIA
5. **Validaciones y mejoras UX** - Prioridad BAJA

## ✅ Checklist Final

- [ ] Todos los formularios tienen campos cíclicos
- [ ] Validaciones frontend implementadas
- [ ] Visualización actualizada en listas/tablas
- [ ] Pruebas manuales completadas
- [ ] Retrocompatibilidad verificada
- [ ] Documentación actualizada
