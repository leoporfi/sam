# **Documentación Técnica: Servicio de Callback (Tiempo Real)**

**Módulo:** sam.callback

## **1\. Propósito**

El **Servicio de Callback** es el "oído" del sistema. Su única función es escuchar. Mientras que el Lanzador tiene que preguntar activamente a A360 "¿ya terminaste?", el Callback permite que A360 nos avise **inmediatamente** cuando un robot finaliza.

Esto reduce la latencia de actualización de minutos (Conciliador) a milisegundos, permitiendo liberar los equipos para el siguiente robot casi al instante.

## **2\. Arquitectura y Seguridad**

Este servicio expone una API REST (FastAPI) ligera. Dado que recibe peticiones externas, la seguridad es su componente más complejo.

### **Mecanismo de Autenticación Dual**

El servicio puede validar dos tipos de credenciales simultáneamente. El comportamiento depende de la variable CALLBACK\_AUTH\_MODE.

1. **Token Estático (X-Authorization):**  
   * Es una clave secreta (API Key) definida por nosotros en SAM y configurada en A360.  
   * **Uso:** Validación simple y rápida.  
2. **Token Dinámico (JWT / Bearer):**  
   * Es un token firmado generado por un API Gateway corporativo (si existe en la infraestructura).  
   * **Uso:** Validación de identidad robusta mediante criptografía asimétrica (Clave Pública/Privada).

### **Modos de Operación (CALLBACK\_AUTH\_MODE)**

* **optional (Recomendado):** La puerta se abre si **cualquiera** de los dos tokens es válido. Es ideal para transiciones o entornos mixtos.  
* **required:** La puerta solo se abre si vienen **ambos** tokens y ambos son válidos. Máxima seguridad.  
* **none:** La puerta está abierta. Solo para pruebas locales. **Prohibido en Producción.**

## **3\. Flujo de Datos**

1. **Disparo:** El robot en A360 termina su tarea (éxito o fallo).  
2. **Notificación:** A360 (o el API Gateway) envía un POST a la URL del callback (ej. https://sam-server/api/callback).  
3. **Validación:** SAM verifica los tokens según el modo configurado.  
4. **Actualización:**  
   * Si es válido: SAM actualiza inmediatamente la tabla Ejecuciones con el estado final (COMPLETED, RUN\_FAILED) y guarda el JSON recibido en la columna CallbackInfo.  
   * Si es inválido: SAM devuelve un error HTTP 401/403 y **ignora** la actualización.

## **4\. Variables de Entorno Requeridas (.env)**

Cualquier cambio requiere reiniciar el servicio SAM\_Callback.

### **Servidor**

* CALLBACK\_SERVER\_PORT: Puerto de escucha (ej. 8008). Asegurarse de que el Firewall de Windows permita este puerto.  
* CALLBACK\_ENDPOINT\_PATH: Ruta relativa (ej. /api/callback).

### **Seguridad**

* CALLBACK\_AUTH\_MODE: optional, required, none.  
* CALLBACK\_TOKEN: El string secreto que debe coincidir con lo configurado en A360.  
* JWT\_PUBLIC\_KEY: (Si se usa JWT) La clave pública para verificar la firma del token del Gateway.

## **5\. Diagnóstico de Fallos (Troubleshooting)**

* **Log:** callback.log  
* **Caso: "El robot terminó hace 10 minutos pero en SAM sigue 'Running'"**  
  1. **Verificar Logs:** Si el log está vacío, la petición **nunca llegó** a SAM.  
     * Causa probable: Firewall bloqueando el puerto o URL mal configurada en A360.  
  2. **Verificar Errores 401/403:** Si el log muestra "Unauthorized", la petición llegó pero la llave es incorrecta.  
     * Acción: Comparar el CALLBACK\_TOKEN del .env con el configurado en A360.  
* **Caso: "A360 da error al invocar el callback"**  
  1. **Prueba Manual:** Usar Postman o curl desde el servidor de A360 hacia el servidor SAM para verificar visibilidad de red.  
  2. **Certificados:** Si la URL es https, verificar que el certificado SSL del servidor SAM sea válido y confiable para A360.  
* **Caso: "El callback llega pero da error 422 Unprocessable Entity"**  
  1. **Formato JSON:** A360 cambió el formato de su respuesta y SAM no lo reconoce.  
  2. **Acción:** Capturar el JSON del log y reportarlo a Desarrollo para actualizar el esquema (schemas.py).