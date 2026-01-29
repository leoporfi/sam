# Novedades de SAM - Enero 2026

Resumen de las mejoras y cambios más importantes implementados en SAM durante este mes.

## 🌟 Lo Nuevo

### 🔔 Sistema de Alertas Inteligente
- **Correos más claros**: Ahora las alertas incluyen emojis (🤖, ⚠️), nombres claros de robots/equipos y detalles técnicos para facilitar la solución de problemas.
- **Menos ruido**: SAM ahora detecta cuando A360 se está reiniciando y evita enviar múltiples alertas repetidas, enviando un aviso de "Recuperación" cuando todo vuelve a la normalidad.
- **Alertas Críticas**: Mejor detección de errores de servidor (500) y configuración (400), con instrucciones claras sobre qué hacer.

### 💻 Interfaz Web
- **Búsqueda Mejorada**: En las pantallas de Robots y Equipos, ahora la búsqueda se activa al presionar **Enter**. ¡Adiós a que se borre el texto mientras escribes!
- **Correcciones Visuales**: Mejoras en la visualización de estados y modales de configuración.

### 🤖 Gestión de Robots
- **Robots Cíclicos**: Soporte completo para ejecuciones cíclicas con ventanas de tiempo personalizadas.
- **Estabilidad**: Mejoras internas (Stored Procedures) que hacen que la asignación y ejecución de robots sea más rápida y confiable.

### ⚙️ Configuración
- **Configuración Dinámica**: Mejoras en cómo SAM gestiona sus configuraciones internas para ser más flexible.
- **Limpieza**: Hemos estandarizado versiones y limpiado código antiguo para mantener el sistema saludable.

---
*Para más detalles técnicos, pueden consultar el archivo `CHANGELOG.md` en la raíz del proyecto.*
