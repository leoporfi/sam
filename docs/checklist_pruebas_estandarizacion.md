# Checklist de Pruebas - Estandarización ReactPy

**Fecha:** 2024-12-19  
**Rama:** `feat/estandarizacion-reactpy`  
**Fases Completadas:** 1, 2, 3, 4

---

## Instrucciones

1. Marca cada ítem con ✅ cuando funcione correctamente
2. Marca con ❌ si hay algún problema (anota el error)
3. Marca con ⚠️ si hay comportamiento inesperado pero no crítico

---

## Pre-requisitos

- [✅] El servidor inicia sin errores: `python -m sam.web.run_web`
- [✅] No hay errores en la consola del navegador (F12 → Console)
- [✅] La aplicación carga en `http://localhost:8000` (o puerto configurado)

---

## 1. Navegación y Estructura General

### 1.1 Navegación entre Páginas
- [✅] Click en "Robots" → Carga página de robots
- [✅] Click en "Equipos" → Carga página de equipos
- [✅] Click en "Pools" → Carga página de pools
- [✅] Click en "Programaciones" → Carga página de programaciones
- [✅] Click en "Mapeos" → Carga página de mapeos
- [✅] Navegación con URL directa funciona (ej: `/equipos`)

### 1.2 Layout General
- [✅] El header/navegación se muestra correctamente
- [⚠️] El tema claro/oscuro funciona (si aplica)
- [✅] No hay elementos rotos o desalineados

---

## 2. Página de Robots (`/`)

### 2.1 Controles y Filtros
- [ ] El panel de controles se muestra correctamente
- [ ] El botón "Controles" (móvil) expande/colapsa el panel
- [ ] El campo de búsqueda funciona (buscar por nombre de robot)
- [ ] El filtro "Activo" funciona (Todos/Activos/Inactivos)
- [ ] El filtro "Online" funciona (Todos/Online/Programados)
- [ ] El botón "Robot" (crear) funciona
- [ ] Los estilos se aplican correctamente (botones, inputs)

### 2.2 Tabla de Robots
- [ ] La tabla se muestra con todas las columnas
- [ ] Los robots se listan correctamente
- [ ] El ordenamiento por columna funciona (click en headers)
- [ ] Los indicadores de ordenamiento (▲/▼) se muestran correctamente
- [ ] Las filas tienen el estilo correcto
- [ ] Los checkboxes de "Activo" y "Online" funcionan
- [ ] Los botones de acción (Editar, Asignar, Programar) funcionan

### 2.3 Tarjetas (Cards) de Robots
- [ ] Las tarjetas se muestran en vista móvil/responsive
- [ ] Cada tarjeta muestra la información correcta
- [ ] Los botones en las tarjetas funcionan

### 2.4 Estados Async
- [ ] **Loading**: Se muestra spinner mientras carga
- [ ] **Error**: Si hay error, se muestra mensaje de error claramente
- [ ] **Vacío**: Si no hay robots, se muestra mensaje "No se encontraron robots"
- [ ] Los estados se muestran con los componentes correctos (AsyncContent)

### 2.5 Paginación
- [ ] La paginación se muestra cuando hay más de 1 página
- [ ] Cambiar de página funciona correctamente
- [ ] El resumen de paginación muestra información correcta

### 2.6 Funcionalidades Específicas
- [ ] El botón "Sincronizar Robots" funciona
- [ ] La sincronización muestra notificaciones correctas
- [ ] Actualizar estado de robot (Activo/Online) funciona
- [ ] Abrir modal de edición funciona
- [ ] Abrir modal de asignación funciona
- [ ] Abrir modal de programación funciona

---

## 3. Página de Equipos (`/equipos`)

### 3.1 Controles y Filtros
- [ ] El panel de controles se muestra correctamente
- [ ] El campo de búsqueda funciona
- [ ] El filtro "Activo" funciona
- [ ] El filtro "Balanceo" funciona
- [ ] El botón "Equipo" (crear) funciona
- [ ] Los estilos se aplican correctamente

### 3.2 Tabla de Equipos
- [ ] La tabla se muestra con todas las columnas
- [ ] Los equipos se listan correctamente
- [ ] El ordenamiento funciona
- [ ] Los checkboxes de "Activo SAM" y "Permite Balanceo" funcionan
- [ ] Los tags de estado se muestran correctamente (Robot, Tipo Asig., Pool)

### 3.3 Tarjetas de Equipos
- [ ] Las tarjetas se muestran correctamente
- [ ] La información se muestra correctamente

### 3.4 Estados Async
- [ ] **Loading**: Spinner mientras carga
- [ ] **Error**: Mensaje de error si hay problema
- [ ] **Vacío**: Mensaje si no hay equipos

### 3.5 Paginación
- [ ] La paginación funciona correctamente

### 3.6 Funcionalidades Específicas
- [ ] Actualizar estado de equipo funciona
- [ ] El switch de balanceo se deshabilita si tiene asignación programada

---

## 4. Página de Pools (`/pools`)

### 4.1 Controles
- [ ] El panel de controles se muestra correctamente
- [ ] El campo de búsqueda funciona
- [ ] El botón "Pool" (crear) funciona
- [ ] Los estilos se aplican correctamente

### 4.2 Tabla/Tarjetas de Pools
- [ ] Los pools se muestran correctamente (tabla o tarjetas)
- [ ] La información de cada pool es correcta (robots, equipos)
- [ ] Los botones de acción (Editar, Asignar, Eliminar) funcionan

### 4.3 Estados Async
- [ ] **Loading**: Spinner mientras carga
- [ ] **Error**: Mensaje de error si hay problema
- [ ] **Vacío**: Mensaje si no hay pools

### 4.4 Funcionalidades Específicas
- [ ] Crear pool funciona
- [ ] Editar pool funciona
- [ ] Asignar robots/equipos a pool funciona
- [ ] Eliminar pool funciona

---

## 5. Página de Programaciones (`/programaciones`)

### 5.1 Controles y Filtros
- [ ] El panel de controles se muestra correctamente
- [ ] El campo de búsqueda funciona
- [ ] El filtro "Tipo" funciona (Diaria/Semanal/Mensual/Específica)
- [ ] El filtro "Robot" funciona
- [ ] Los estilos se aplican correctamente

### 5.2 Tabla/Tarjetas de Programaciones
- [ ] Las programaciones se muestran correctamente
- [ ] La información es correcta (robot, tipo, hora, detalles)
- [ ] Los botones de acción funcionan

### 5.3 Estados Async
- [ ] **Loading**: Spinner mientras carga
- [ ] **Error**: Mensaje de error si hay problema
- [ ] **Vacío**: Mensaje si no hay programaciones

### 5.4 Paginación
- [ ] La paginación funciona correctamente

### 5.5 Funcionalidades Específicas
- [ ] Toggle de estado (Activo/Inactivo) funciona
- [ ] Editar programación funciona
- [ ] Asignar equipos a programación funciona

---

## 6. Página de Mapeos (`/mapeos`)

### 6.1 Funcionalidad Básica
- [ ] La página carga correctamente
- [ ] Los mapeos se muestran correctamente
- [ ] Crear mapeo funciona
- [ ] Eliminar mapeo funciona

---

## 7. Verificación de Estilos Centralizados

### 7.1 Botones
- [ ] Los botones primarios tienen el estilo correcto (azul/primary)
- [ ] Los botones secundarios tienen el estilo correcto
- [ ] Los botones outline tienen el estilo correcto
- [ ] Los botones de acción tienen iconos correctos

### 7.2 Tags/Badges
- [ ] Los tags de estado se muestran con colores correctos
- [ ] Los tags "Programado" vs "Dinámico" tienen estilos diferentes
- [ ] Los tags "N/A" tienen estilo secondary

### 7.3 Contenedores
- [ ] Las tarjetas (cards) tienen el estilo correcto
- [ ] Los contenedores de tabla tienen el estilo correcto
- [ ] Los paneles colapsables funcionan correctamente

### 7.4 Consistencia Visual
- [ ] Todos los componentes tienen estilos consistentes
- [ ] No hay estilos rotos o faltantes
- [ ] Los espaciados son consistentes

---

## 8. Verificación de Componentes Base

### 8.1 AsyncContent
- [ ] El componente LoadingSpinner se muestra correctamente
- [ ] El componente ErrorAlert muestra errores correctamente
- [ ] El componente EmptyState muestra mensaje cuando no hay datos
- [ ] La transición entre estados es suave

### 8.2 DataTable (si se usa)
- [ ] La tabla genérica funciona correctamente (si se implementó)
- [ ] El ordenamiento funciona
- [ ] Las acciones funcionan

---

## 9. Verificación de Hooks

### 9.1 Funcionalidad de Hooks
- [ ] Los hooks cargan datos correctamente
- [ ] Los hooks manejan errores correctamente
- [ ] Los hooks actualizan el estado correctamente
- [ ] Los hooks responden a cambios de filtros/paginación

### 9.2 Performance
- [ ] No hay renders innecesarios
- [ ] Los datos se cargan de forma eficiente
- [ ] No hay memory leaks aparentes

---

## 10. Modales

### 10.1 Modales de Robots
- [ ] Modal de edición de robot se abre/cierra correctamente
- [ ] Modal de asignación se abre/cierra correctamente
- [ ] Modal de programación se abre/cierra correctamente
- [ ] Los formularios en modales funcionan

### 10.2 Modales de Equipos
- [ ] Modal de edición de equipo funciona

### 10.3 Modales de Pools
- [ ] Modal de edición de pool funciona
- [ ] Modal de asignación funciona

### 10.4 Modales de Programaciones
- [ ] Modal de edición de programación funciona
- [ ] Modal de asignación de equipos funciona

---

## 11. Notificaciones

### 11.1 Notificaciones de Éxito
- [ ] Las notificaciones de éxito se muestran correctamente
- [ ] Las notificaciones desaparecen automáticamente

### 11.2 Notificaciones de Error
- [ ] Las notificaciones de error se muestran correctamente
- [ ] Los mensajes de error son claros y útiles

### 11.3 Notificaciones de Info
- [ ] Las notificaciones informativas se muestran (ej: sincronización)

---

## 12. Verificación de Consola del Navegador

### 12.1 Errores JavaScript
- [ ] No hay errores en la consola (F12 → Console)
- [ ] No hay warnings críticos
- [ ] No hay errores de importación

### 12.2 Network
- [ ] Las peticiones API se realizan correctamente
- [ ] No hay peticiones fallidas (404, 500, etc.)
- [ ] Las respuestas son correctas

---

## 13. Verificación de Compatibilidad

### 13.1 Navegadores
- [ ] Funciona en Chrome/Edge (recomendado)
- [ ] Funciona en Firefox (si aplica)
- [ ] Funciona en Safari (si aplica)

### 13.2 Responsive
- [ ] La aplicación funciona en desktop
- [ ] La aplicación funciona en tablet (si aplica)
- [ ] La aplicación funciona en móvil (si aplica)
- [ ] Los paneles colapsables funcionan en móvil

---

## 14. Verificación de Funcionalidades Críticas

### 14.1 CRUD Completo
- [ ] **Create**: Crear robot/equipo/pool funciona
- [ ] **Read**: Leer/listar datos funciona
- [ ] **Update**: Actualizar datos funciona
- [ ] **Delete**: Eliminar funciona (si aplica)

### 14.2 Sincronización
- [ ] Sincronizar robots funciona
- [ ] Sincronizar equipos funciona
- [ ] Las notificaciones de sincronización son correctas

### 14.3 Filtros y Búsqueda
- [ ] Todos los filtros funcionan correctamente
- [ ] La búsqueda funciona en tiempo real (con debounce)
- [ ] Los filtros se combinan correctamente

---

## 15. Verificación de Type Safety

### 15.1 Type Hints
- [ ] No hay errores de tipo en la consola (si hay validación)
- [ ] Los componentes reciben los tipos correctos

---

## Resumen de Problemas Encontrados

### Problemas Críticos (Bloquean funcionalidad)
```
1. 
2. 
3. 
```

### Problemas Menores (No bloquean pero deben corregirse)
```
1. 
2. 
3. 
```

### Observaciones
```
1. 
2. 
3. 
```

---

## Resultado Final

- [ ] ✅ **TODO FUNCIONA CORRECTAMENTE** - Puedo continuar con las siguientes fases
- [ ] ⚠️ **HAY PROBLEMAS MENORES** - Puedo continuar pero deben corregirse
- [ ] ❌ **HAY PROBLEMAS CRÍTICOS** - Debo detenerme y corregir antes de continuar

---

## Notas Adicionales

```
[Espacio para notas adicionales durante las pruebas]




```

---

**Fecha de Pruebas:** _______________  
**Probado por:** _______________  
**Versión:** `feat/estandarizacion-reactpy` (Fases 1-4 completadas)

