# **SAM: Sistema Automático de Robots**

SAM es un ecosistema de orquestación de RPA diseñado para gestionar, lanzar, balancear y monitorear la ejecución de robots construidos sobre la plataforma **Automation 360**.

A diferencia del agendador nativo de A360, SAM añade una capa de inteligencia para el manejo de colas, priorización dinámica y balanceo de carga entre pools de equipos.

## **Arquitectura del Sistema**

El sistema opera mediante **4 microservicios independientes** que corren como servicios de Windows (NSSM) y se comunican a través de una base de datos central (SQL Server).

### **1\. Servicio Lanzador (sam.lanzador)**

* **Rol:** El Motor.
* **Función:** Consulta la BD, despierta a los robots a través de la API de A360 y monitorea que terminen correctamente.
* **Punto Crítico:** Maneja la lógica de estados UNKNOWN (cuando A360 pierde conexión) y sincroniza los catálogos de robots.

### **2\. Servicio Balanceador (sam.balanceador)**

* **Rol:** El Estratega.
* **Función:** Monitorea la demanda (tickets pendientes) y asigna/quita equipos a los robots dinámicamente.
* **Punto Crítico:** Maneja la **Preemption** (prioridad estricta) y el **Cooling** (tiempos de espera para estabilizar pools).

### **3\. Servicio Callback (sam.callback)**

* **Rol:** El Oído (Tiempo Real).
* **Función:** Recibe notificaciones inmediatas desde A360 cuando un bot termina, actualizando la BD al instante.
* **Punto Crítico:** Requiere que el puerto del servicio (default 8008\) esté accesible desde el Control Room de A360.

### **4\. Interfaz de Gestión (sam.web)**

* **Rol:** La Consola (ABM).
* **Función:** Permite al equipo de soporte configurar el sistema:
  * Alta/Baja de Robots y Equipos.
  * Asignación de Prioridades (1-10).
  * Gestión de Pools y Mapeos.
  * Programación de Tareas (Schedules).

## **📍 Guía Rápida para Soporte y Operaciones**

### **Ubicación de Componentes**

* **Directorio de Instalación:** C:\\RPA\\sam (Verificar en servidor).
* **Logs:** C:\\RPA\\Logs\\SAM (Rotativos por servicio).
* **Gestor de Servicios:** Windows Services (services.msc).
* **Entorno Python:** Gestionado con uv.

### **Comandos de Gestión (PowerShell Admin)**

Los servicios se gestionan vía NSSM pero aparecen como servicios estándar de Windows.

**Reiniciar un servicio (Ej. tras cambiar el .env):**

Restart-Service SAM\_Lanzador
Restart-Service SAM\_Balanceador
Restart-Service SAM\_Callback
Restart-Service SAM\_Web

**Ver estado de los servicios:**

Get-Service SAM\_\*

### **Diagnóstico Básico (Logs)**

| Archivo Log | Qué buscar |
| :---- | :---- |
| lanzador.log | Fallos de despliegue ("DeviceNotActive"), errores de API A360, robots "zombies". |
| balanceador.log | Por qué no se asignan máquinas ("Cooling", "Prioridad"), errores de conexión con Clouders. |
| callback.log | Si llegan las peticiones de A360. Si hay errores 401 (Token inválido). |
| web.log | Errores internos de la interfaz o fallos de validación de datos. |

## **🚀 Instalación y Despliegue**

### **Prerrequisitos**

* **Python 3.9+**
* **SQL Server** (Base de datos creada con SAM.sql).
* **NSSM** (Non-Sucking Service Manager) en el PATH.
* **UV** (pip install uv).

### **Instalación en Producción (Windows)**

1. Clonar el repositorio.
2. Configurar el archivo .env (usar .env.example como base).
3. Ejecutar el script de instalación (requiere permisos de Admin):
   .\\scripts\\install\_services.ps1

   *Este script crea el entorno virtual, instala dependencias y registra los servicios de Windows.*

### **Ejecución en Desarrollo**

uv run \-m sam.lanzador
uv run \-m sam.balanceador
uv run \-m sam.callback
uv run \-m sam.web

## **Documentación Detallada**

Para profundizar en la lógica interna de cada módulo, consultar:

* [Servicio Lanzador](docs/servicios/servicio_lanzador.md)
* [Servicio Balanceador](docs/servicios/servicio_balanceador.md)
* [Servicio Callback](docs/servicios/servicio_callback.md)
* [Interfaz Web](docs/servicios/servicio_web.md)
