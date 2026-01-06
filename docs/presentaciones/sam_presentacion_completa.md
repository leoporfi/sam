# Presentación del Proyecto SAM (Sistema de Asignación y Monitoreo)
## Versión Integrada - Máximo 10 Diapositivas

---

## DIAPOSITIVA 1: Portada
**Título:** Sistema SAM - Orquestador Inteligente de RPA
**Subtítulo:** Sistema de Asignación y Monitoreo para Automation 360
**Elementos visuales sugeridos:**
- Logo o ícono representativo del proyecto
- Fondo tecnológico moderno
- Fecha de presentación

---

## DIAPOSITIVA 2: ¿Qué es SAM?
**Título:** Visión General del Sistema

**Contenido:**
SAM es un orquestador inteligente que optimiza la ejecución de robots RPA en Automation 360, gestionando equipos (VMs) de forma dinámica y eficiente.

**Componentes principales:**
- 🎯 **Lanzador**: Motor de ejecución
- ⚖️ **Balanceador**: Optimizador de equipos (VMs)
- 📞 **Callback**: Notificaciones en tiempo real
- 🖥️ **Web**: Consola de administración

**Analogía clave:** SAM funciona como un centro de control logístico que asigna conductores (equipos) a servicios (robots) según la demanda en tiempo real.

---

## DIAPOSITIVA 3: Servicio Lanzador - El Motor Principal
**Título:** Lanzador: Core del Sistema

**Funciones principales:**
1. **Desplegador** 🚀
   - Ejecuta robots en Automation 360
   - Respeta ventanas de mantenimiento
   - Gestiona concurrencia (max workers)

2. **Conciliador** 🔍
   - Audita estados de ejecución
   - Maneja estados UNKNOWN (<2h vs >2h)
   - Limpia ejecuciones huérfanas

3. **Sincronizador** 🔄
   - Actualiza catálogos de robots, equipos y usuarios
   - Sincronización automática cada hora

**Ciclos de ejecución:** 15 seg (lanzamiento) | 5-15 min (conciliación) | 1 hora (sincronización)

---

## DIAPOSITIVA 4: Servicio Balanceador - La Inteligencia
**Título:** Balanceador: Optimización de Equipos

**¿Qué hace?**
Ajusta dinámicamente la asignación de equipos según la demanda de trabajo pendiente.

**Componentes clave:**
- **Proveedores de Carga** 👁️: Consultan Clouders API y RPA360 BD
- **Algoritmo de Balanceo** 🧠: Decide scaling out/in según carga
- **Cooling Manager** ❄️: Evita cambios bruscos (período de enfriamiento)

**Conceptos críticos:**
- **Preemption**: Prioridad estricta (1=alta, 10=baja)
- **Aislamiento de Pool**: Recursos exclusivos vs compartidos
- **Mapeos**: Traducción de nombres externos a internos

**Frecuencia:** Ciclo cada 60 segundos

---

## DIAPOSITIVA 5: Servicio Callback - Tiempo Real
**Título:** Callback: El Oído del Sistema

**Propósito:**
Reducir latencia de actualización de minutos a milisegundos mediante notificaciones instantáneas desde A360.

**Seguridad - Autenticación Dual:**
1. **Token Estático** (X-Authorization): API Key compartida
2. **Token Dinámico** (JWT/Bearer): Firmado criptográficamente

**Modos de operación:**
- `optional`: Cualquier token válido ✅
- `required`: Ambos tokens obligatorios 🔒
- `none`: Sin validación (solo desarrollo) ⚠️

**Flujo:** A360 termina → POST a SAM → Validación → Actualización instantánea

---

## DIAPOSITIVA 6: Interfaz Web - Control Central
**Título:** Web: Consola de Administración

**Funcionalidades ABM:**
1. **Robots** 🤖: Prioridad, límites de concurrencia
2. **Equipos** 💻: Habilitar/deshabilitar, estado
3. **Pools** 🏊: Agrupaciones lógicas, aislamiento
4. **Mapeos** 🗺️: Equivalencias nombre externo ↔ interno
5. **Schedules** ⏰: Programación CRON

**Stack tecnológico:**
- Backend: FastAPI (Python)
- Frontend: ReactPy (Python)
- BD: SQL Server (Stored Procedures)

**Puerto por defecto:** 8000

---

## DIAPOSITIVA 7: Arquitectura de Integración
**Título:** Ecosistema SAM

**Diagrama sugerido:**
```
[Clouders API] ──┐
[RPA360 BD]    ──┤──> [BALANCEADOR] ──> [BD SAM] <──> [WEB]
                 │                          ↕
[A360 API]    <──┴─────── [LANZADOR] ──────┘
                              ↓
                         [CALLBACK] <──── [A360 Notif]
```

**Flujo de datos:**
1. Balanceador detecta carga externa
2. Asigna equipos a robots en BD
3. Lanzador ejecuta en A360
4. Callback actualiza estados en tiempo real
5. Web permite supervisión y ajustes

---

## DIAPOSITIVA 8: Configuración Dinámica
**Título:** Gestión Sin Reinicio

**Tabla ConfiguracionSistema** (cambios en caliente):
| Parámetro | Opciones | Impacto |
|-----------|----------|---------|
| `BALANCEADOR_POOL_AISLAMIENTO_ESTRICTO` | true/false | Préstamo entre pools |
| `BALANCEADOR_LOG_LEVEL` | DEBUG/INFO | Verbosidad logs |
| `GLOBAL_MAINTENANCE_MODE` | true/false | Pausa global |

**Variables .env** (requieren reinicio):
- Intervalos de ciclos
- Credenciales externas (Clouders, A360)
- Períodos de cooling/pausa

**Ventaja:** Ajustes operacionales rápidos sin interrupciones

---

## DIAPOSITIVA 9: Casos de Soporte Críticos
**Título:** Troubleshooting Rápido

**Problema 1:** Robot con carga pero sin máquinas
- ✅ Verificar mapeos en Web
- ✅ Confirmar período de cooling no activo
- ✅ Revisar log: "Carga detectada para..."

**Problema 2:** Robot terminó pero sigue "Running"
- ✅ Callback: verificar conectividad/autenticación
- ✅ Conciliador: revisar estado UNKNOWN
- ✅ Firewall: puerto 8008 abierto

**Problema 3:** Robot no arranca
- ✅ Equipo offline en A360
- ✅ Ventana de pausa activa (23:00-06:00)
- ✅ Log lanzador: errores de API

**Logs principales:** lanzador.log | balanceador.log | callback.log | web.log

---

## DIAPOSITIVA 10: Beneficios y Próximos Pasos
**Título:** Valor del Sistema SAM

**Beneficios cuantificables:**
- ⚡ Reducción latencia: Minutos → Milisegundos (Callback)
- 🎯 Optimización automática: Asignación dinámica según demanda
- 🛡️ Alta disponibilidad: Detección y limpieza de zombies
- 📊 Visibilidad total: Dashboard centralizado
- 🔄 Extensibilidad: Nuevos proveedores de carga plug & play

**Próximos pasos:**
1. Integración con ServiceNow/Jira (nuevos proveedores)
2. Dashboard de métricas en tiempo real
3. Machine Learning para predicción de carga
4. Alertas proactivas (Slack/Teams)

**Contacto:** [Equipo de Soporte/Desarrollo]
