# Scripts de Prueba: Robots Cíclicos con Ventanas

Scripts para probar la funcionalidad de robots cíclicos con ventanas temporales.

## 📁 Archivos

### Python
- **probar_api_ciclicos.py** - ⭐ Pruebas completas de API (recomendado)
  - Obtiene IDs dinámicamente
  - Prueba 3 escenarios diferentes
  - Muestra resultados detallados

- **probar_ciclicos.py** - Pruebas directas a base de datos
  - Requiere conexión directa a BD
  - Útil para debugging

- **probar_programacion_ciclica_simple.py** - Versión simplificada
- **test_programacion_ciclica.py** - Tests unitarios

### PowerShell
- **probar_api_simple.ps1** - Pruebas de API desde PowerShell
  - Obtiene IDs dinámicamente
  - Similar a probar_api_ciclicos.py pero en PowerShell

## 🚀 Uso

### Prueba Completa (Python)
```bash
python probar_api_ciclicos.py
```

### Prueba Simple (PowerShell)
```powershell
.\probar_api_simple.ps1
```

## 📋 Pruebas Incluidas

1. **Programación Cíclica Simple**
   - Horario: 09:00 - 17:00
   - Intervalo: 30 minutos

2. **Programación Cíclica con Ventana de Fechas**
   - Semanal (Lun-Vie)
   - Horario: 08:00 - 18:00
   - Ventana: 2025-01-01 a 2025-12-31
   - Intervalo: 60 minutos

3. **Retrocompatibilidad**
   - Programación tradicional (sin nuevos campos)
   - Verifica que sigue funcionando

## ✅ Resultado Esperado

Todas las pruebas deben mostrar:
```
[OK] Programacion creada exitosamente!
Status Code: 200
```

## 🔧 Requisitos

- Servicio web corriendo en `http://localhost:8000`
- Base de datos migrada (ver `migrations/robots-ciclicos/`)
- Al menos un robot y un equipo activos en la BD
