# Guía de Verificación de Cambios - Fix Hook Stack Error

## ✅ Pasos para Verificar que los Cambios Funcionan

### 1. Prueba Local (Recomendado antes de producción)

#### A. Iniciar el servicio localmente
```powershell
# Desde el directorio del proyecto
cd C:\Users\lporfiri\RPA\sam
python -m sam.web
# O si usas uv:
uv run -m sam.web
```

#### B. Acceder a la interfaz web
- Abre el navegador en: `http://127.0.0.1:8000` (o el puerto configurado)
- Navega a la página de Robots: `http://127.0.0.1:8000/`

#### C. Verificar en la consola del navegador
1. Abre las **Herramientas de Desarrollador** (F12)
2. Ve a la pestaña **Console**
3. **Busca errores** relacionados con:
   - `Hook stack is in an invalid state`
   - `RuntimeError`
   - Errores de ReactPy

#### D. Probar funcionalidades críticas
- ✅ Cargar la página de Robots
- ✅ Filtrar robots (búsqueda, activos, online)
- ✅ Cambiar páginas
- ✅ Abrir modales (editar, asignaciones, programaciones)
- ✅ Sincronizar robots
- ✅ Actualizar estado de robots

### 2. Verificar Logs del Servicio

#### A. Monitorear el log en tiempo real
```powershell
# En PowerShell, monitorea el log
Get-Content logs\sam_interfaz_web.log -Wait -Tail 50
```

#### B. Buscar errores específicos
```powershell
# Buscar si aún aparecen los errores
Select-String -Path logs\sam_interfaz_web.log -Pattern "Hook stack is in an invalid state"
Select-String -Path logs\sam_interfaz_web.log -Pattern "RuntimeError.*Hook"
```

**Resultado esperado:** No deberían aparecer resultados (0 matches)

#### C. Verificar que el servicio funciona normalmente
```powershell
# Buscar mensajes de error recientes
Select-String -Path logs\sam_interfaz_web.log -Pattern "ERROR" | Select-Object -Last 20
```

### 3. Prueba en Producción (Después del despliegue)

#### A. Reiniciar el servicio Windows (NSSM)
```powershell
# Detener el servicio
nssm stop sam_interfaz_web

# Esperar unos segundos
Start-Sleep -Seconds 5

# Iniciar el servicio
nssm start sam_interfaz_web

# Verificar estado
nssm status sam_interfaz_web
```

#### B. Monitorear logs de producción
```powershell
# Monitorear el log en tiempo real
Get-Content C:\RPA\sam\logs\sam_interfaz_web.log -Wait -Tail 50
```

#### C. Verificar que no hay errores nuevos
- Observa el log durante 5-10 minutos
- Navega por la interfaz web
- Realiza acciones que antes causaban errores
- **Resultado esperado:** No deberían aparecer errores de "Hook stack is in an invalid state"

### 4. Pruebas Específicas de Funcionalidad

#### A. Página de Robots
1. Acceder a `/` o `/robots`
2. Verificar que los robots se cargan correctamente
3. Probar filtros:
   - Búsqueda por nombre
   - Filtro de activos/inactivos
   - Filtro online/programados
4. Cambiar de página
5. Ordenar por columnas

#### B. Modales
1. Click en "Editar" de un robot
2. Click en "Asignaciones"
3. Click en "Programaciones"
4. Verificar que los modales se abren sin errores

#### C. Sincronización
1. Click en "Sincronizar Robots"
2. Verificar que el proceso se completa sin errores
3. Verificar que la lista se actualiza correctamente

### 5. Verificación Automática con Script (Recomendado)

#### A. Ejecutar el script de verificación
```powershell
# Desde el directorio raíz del proyecto
python scripts\verificar_fix_hooks.py
```

El script verificará automáticamente:
- ✅ Sintaxis de los archivos de hooks
- ✅ Orden correcto de llamadas a hooks (incondicionales)
- ✅ Ausencia de hooks dentro de bloques condicionales
- ✅ Errores en los logs relacionados con hooks

**Resultado esperado:**
```
✅ VERIFICACIÓN EXITOSA
  ✓ Exitosas: 4
  ⚠ Advertencias: 0
  ✗ Errores: 0
```

#### B. Verificar logs específicos
```powershell
# Verificar un log específico
python scripts\verificar_fix_hooks.py --log-path C:\RPA\sam\logs\sam_interfaz_web.log
```

#### C. Omitir verificación de logs
```powershell
# Solo verificar código, no logs
python scripts\verificar_fix_hooks.py --skip-logs
```

### 6. Verificación Manual de Código (Opcional)

#### A. Verificar que los cambios están aplicados
```powershell
# Verificar que use_app_context() se llama incondicionalmente
Select-String -Path src\sam\web\frontend\hooks\*.py -Pattern "use_app_context\(\)" -Context 2,2
```

**Resultado esperado:** `use_app_context()` debe estar **antes** de cualquier `if api_client is None:`

#### B. Verificar sintaxis Python
```powershell
# Verificar que no hay errores de sintaxis
python -m py_compile src\sam\web\frontend\hooks\use_robots_hook.py
python -m py_compile src\sam\web\frontend\hooks\use_equipos_hook.py
python -m py_compile src\sam\web\frontend\hooks\use_pools_hook.py
python -m py_compile src\sam\web\frontend\hooks\use_schedules_hook.py
```

### 7. Checklist de Verificación

- [ ] Servicio inicia sin errores
- [ ] No hay errores en la consola del navegador
- [ ] No aparecen errores "Hook stack is in an invalid state" en logs
- [ ] La página de Robots carga correctamente
- [ ] Los filtros funcionan
- [ ] Los modales se abren sin errores
- [ ] La sincronización funciona
- [ ] No hay errores nuevos en los logs después de 10 minutos de uso

### 8. Si Encuentras Problemas

#### A. Revisar logs detallados
```powershell
# Ver últimos 100 líneas del log
Get-Content logs\sam_interfaz_web.log -Tail 100
```

#### B. Verificar versión de ReactPy
```powershell
# Verificar versión instalada
python -m pip show reactpy
```

#### C. Limpiar caché del navegador
- Presiona `Ctrl + Shift + Delete`
- Limpia caché y cookies
- Recarga la página con `Ctrl + F5`

---

## 📝 Notas Importantes

1. **Los cambios son compatibles con el código existente** - No deberían romper funcionalidad existente
2. **El problema era específico de producción** - Puede que no se reproduzca en desarrollo
3. **Monitorear durante al menos 30 minutos** después del despliegue para asegurar estabilidad

## 🔍 Indicadores de Éxito

✅ **Éxito:** No aparecen errores "Hook stack is in an invalid state" en los logs  
✅ **Éxito:** La interfaz web funciona normalmente sin errores en consola  
✅ **Éxito:** Todas las funcionalidades (filtros, modales, sincronización) funcionan correctamente

