# Servidor de Callbacks SAM

## Descripción General

Este servicio es un servidor backend WSGI diseñado para recibir notificaciones (callbacks) HTTP desde **Automation Anywhere A360**. Su función principal es escuchar las actualizaciones de estado de las ejecuciones de bots, validar la autenticidad de cada llamada y registrar los resultados en la base de datos de SAM.


## Características Principales

* **Servidor de Producción**: Utiliza **Waitress**, un servidor WSGI de alto rendimiento, cuando está disponible. Proporciona un fallback a `wsgiref` para desarrollo.
* **Seguridad Mejorada**: Requiere un token de autenticación a través del encabezado `X-Authorization` y utiliza una comparación segura (`hmac.compare_digest`) para prevenir ataques de temporización.
* **Código Limpio y Mantenible**: La lógica de negocio está claramente separada de la lógica del servidor. El código utiliza constantes y clases de configuración para evitar valores "mágicos".
* **Configuración Centralizada**: Toda la configuración se gestiona a través de un archivo `.env` en la raíz del proyecto, facilitando el despliegue en diferentes entornos.
* **Logging**: Genera logs detallados en archivos que rotan diariamente, utilizando un manejador de archivos robusto para evitar pérdidas de logs.
* **Manejo de Errores Estructurado**: Utiliza excepciones personalizadas para un control de flujo claro y respuestas de error predecibles y consistentes.
* **Parada Elegante (Graceful Shutdown)**: Captura señales del sistema (como `Ctrl+C`) para cerrar la conexión a la base de datos y registrar estadísticas finales antes de terminar.

## Instalación

1.  Clona el repositorio.
2.  Asegúrate de tener Python 3.8 o superior.
3.  Se recomienda crear un entorno virtual:
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    ```
4.  Instala las dependencias. Asumiendo que existe un archivo `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```
    Dependencias clave: `waitress`, `python-dotenv`, `pyodbc`.

## Configuración (`.env`)

Crea un archivo llamado `.env` en la **raíz del proyecto** (fuera de la carpeta `src`). Usa el siguiente ejemplo como plantilla:

```dotenv
# .env.example

# --- Configuración del Servidor de Callbacks ---
CALLBACK_HOST=0.0.0.0
CALLBACK_PORT=8008
CALLBACK_THREADS=10

# --- Token de seguridad para A360 ---
# Este token debe ser enviado por A360 en el encabezado X-Authorization
CALLBACK_TOKEN="un-token-secreto-muy-largo-y-dificil-de-adivinar"

# --- Configuración de la Base de Datos SAM ---
SQL_SAM_SERVER=tu-servidor-sql.database.windows.net
SQL_SAM_DB_NAME=SAM_DATABASE
SQL_SAM_USER=tu_usuario
SQL_SAM_PASSWORD=tu_contraseña

# --- Configuración de Logs ---
LOG_DIRECTORY="C:/RPA/Logs/SAM"
CALLBACK_LOG_FILENAME="sam_callback_server.log"
LOG_LEVEL="INFO" # DEBUG, INFO, WARNING, ERROR
```

## Cómo Ejecutar el Servicio

Para iniciar el servidor, ejecuta el script `run_callback.py` desde la raíz del proyecto. El script se encargará de configurar el `sys.path` correctamente.

```bash
python src/callback/run_callback.py
```

El servidor imprimirá en la consola la dirección en la que está escuchando y el tipo de servidor que está utilizando (Waitress o wsgiref).

## Funcionamiento de la API

* **Endpoint**: `POST /`
* **Encabezado Requerido**: `X-Authorization: <tu-token-secreto>`
* **Cuerpo de la Solicitud (Request Body)**: Un objeto JSON con la siguiente estructura:
    ```json
    {
      "deploymentId": "string",
      "status": "string",
      "botOutput": {}
    }
    ```
* **Respuestas**: El servidor responderá con códigos de estado HTTP estándar (`200`, `400`, `401`, `405`, `413`, `500`) y un cuerpo JSON que describe el resultado.

## Logging

Los logs se guardan por defecto en la ruta especificada por `LOG_DIRECTORY` en el archivo `.env`. El archivo de log para este servicio es `sam_callback_server.log` y rota cada noche a medianoche.