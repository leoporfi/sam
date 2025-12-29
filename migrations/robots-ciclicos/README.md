# Migración: Robots Cíclicos con Ventanas

Esta carpeta contiene todos los scripts SQL y documentación relacionados con la migración de robots cíclicos con ventanas temporales.

## 📁 Estructura

```
migrations/robots-ciclicos/
├── sql/
│   ├── EJECUTAR_MIGRACION_COMPLETA.sql    # Script maestro (ejecutar este)
│   ├── migration_robots_ciclicos_ventanas.sql  # Migración de tabla
│   ├── update_stored_procedures_ciclicos.sql   # Actualización de SPs principales
│   ├── update_ActualizarProgramacionSimple.sql # Actualización de SP simple
│   ├── optimizacion_ObtenerRobotsEjecutables.sql # Optimización de rendimiento
│   ├── validaciones/                          # Scripts de validación
│   │   ├── verificar_backend_listo_FUNCIONAL.sql  # ⭐ Usar este para verificar
│   │   ├── validacion_pre_migracion.sql
│   │   ├── validacion_post_migracion.sql
│   │   └── analisis_solapamientos_detallado.sql
│   └── fixes/                                 # Scripts de corrección
│       ├── FIX_ObtenerRobotsEjecutables.sql
│       └── FIX_RAPIDO_ObtenerRobotsEjecutables.sql
└── README.md (este archivo)
```

## 🚀 Orden de Ejecución

### 1. Migración Principal
```sql
-- Ejecutar en SSMS:
EJECUTAR_MIGRACION_COMPLETA.sql
```

Este script ejecuta todo en el orden correcto:
1. `migration_robots_ciclicos_ventanas.sql` - Agrega columnas nuevas
2. `update_stored_procedures_ciclicos.sql` - Actualiza SPs principales
3. `update_ActualizarProgramacionSimple.sql` - Actualiza SP simple
4. `optimizacion_ObtenerRobotsEjecutables.sql` - Optimiza rendimiento

### 2. Verificación
```sql
-- Después de la migración, ejecutar:
validaciones/verificar_backend_listo_FUNCIONAL.sql
```

Debería mostrar "5 de 5" parámetros para cada SP.

## 📋 Scripts por Categoría

### Migración
- **EJECUTAR_MIGRACION_COMPLETA.sql** - Script maestro (ejecutar este primero)
- **migration_robots_ciclicos_ventanas.sql** - Agrega columnas a tabla Programaciones
- **update_stored_procedures_ciclicos.sql** - Actualiza CrearProgramacion, ActualizarProgramacionCompleta, ObtenerRobotsEjecutables
- **update_ActualizarProgramacionSimple.sql** - Actualiza ActualizarProgramacionSimple
- **optimizacion_ObtenerRobotsEjecutables.sql** - Agrega índices y optimiza rendimiento

### Validaciones
- **verificar_backend_listo_FUNCIONAL.sql** - ⭐ Verificación final (usar este)
- **validacion_pre_migracion.sql** - Validación antes de migrar
- **validacion_post_migracion.sql** - Validación después de migrar
- **analisis_solapamientos_detallado.sql** - Análisis de solapamientos

### Fixes
- **FIX_ObtenerRobotsEjecutables.sql** - Corrección de errores en SP
- **FIX_RAPIDO_ObtenerRobotsEjecutables.sql** - Corrección rápida

## ✅ Checklist de Migración

- [ ] Ejecutar `EJECUTAR_MIGRACION_COMPLETA.sql`
- [ ] Ejecutar `validaciones/verificar_backend_listo_FUNCIONAL.sql`
- [ ] Verificar que todos los SPs muestren "5 de 5" parámetros
- [ ] Probar creación de programación cíclica desde API

## 📚 Documentación

Ver `docs/robots-ciclicos/` para:
- README principal
- Guía de pruebas
- Análisis de compatibilidad
- Ejemplos de uso
