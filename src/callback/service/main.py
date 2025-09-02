# SAM/src/callback/service/main.py
import hmac
import logging
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.common.database.sql_client import DatabaseConnector
from src.common.utils.config_manager import ConfigManager

# --- Configuración Inicial ---
logger = logging.getLogger(__name__)

# Cargar configuración del servicio de callback
cb_config = ConfigManager.get_callback_server_config()
sql_config = ConfigManager.get_sql_server_config("SQL_SAM")


# --- Modelos de Datos (Pydantic) ---
class CallbackPayload(BaseModel):
    """
    Define la estructura y valida el cuerpo de la petición de callback.
    """

    deployment_id: str = Field(..., alias="deploymentId", description="ID único del despliegue en A360.")
    status: str = Field(..., description="Estado final de la ejecución del bot.")
    device_id: Optional[str] = Field(None, alias="deviceId")
    user_id: Optional[int] = Field(None, alias="userId")
    bot_output: Optional[Dict[str, Any]] = Field(None, alias="botOutput")


class StandardResponse(BaseModel):
    """
    Define el formato de respuesta JSON estándar para toda la API.
    """

    status: str
    message: str


# --- Inicialización de la Aplicación y Recursos ---
app = FastAPI(
    title="SAM Callback Service",
    description="Servicio para recibir y procesar notificaciones de Automation Anywhere A360.",
    version="2.0.0",
)

db_connector: Optional[DatabaseConnector] = None


@app.on_event("startup")
def startup_event():
    """
    Evento de inicio: Inicializa el conector de la base de datos.
    """
    global db_connector
    logger.info("Inicializando el conector de la base de datos para FastAPI...")
    try:
        db_connector = DatabaseConnector(
            servidor=sql_config["server"], base_datos=sql_config["database"], usuario=sql_config["uid"], contrasena=sql_config["pwd"]
        )
        logger.info("Conector de base de datos inicializado exitosamente.")
    except Exception as e:
        logger.critical(f"No se pudo inicializar el conector de la base de datos: {e}", exc_info=True)
        db_connector = None


@app.on_event("shutdown")
def shutdown_event():
    """
    Evento de cierre: Cierra la conexión a la base de datos de forma segura.
    """
    if db_connector:
        logger.info("Cerrando la conexión de la base de datos.")
        db_connector.cerrar_conexion()


# --- Manejadores de Excepciones Personalizados ---
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Captura las excepciones HTTP y formatea la respuesta para que coincida con el formato estándar.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "ERROR", "message": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Captura los errores de validación de Pydantic y los formatea.
    """
    # Se puede personalizar para ser más detallado si es necesario
    error_message = exc.errors()[0]["msg"] if exc.errors() else "Error de validación"
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"status": "ERROR", "message": error_message},
    )


# --- Dependencias de FastAPI ---
def get_db() -> DatabaseConnector:
    """
    Dependencia de FastAPI para obtener el conector de base de datos.
    """
    if not db_connector:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="La conexión con la base de datos no está disponible.")
    return db_connector


async def verify_token(x_authorization: Optional[str] = Header(None, alias="X-Authorization")):
    """
    Dependencia de seguridad para validar el token de autorización.
    """
    auth_token = cb_config.get("callback_token")
    auth_mode = cb_config.get("auth_mode", "strict").lower()

    if auth_mode == "strict":
        if not auth_token:
            logger.error("Error de configuración del servidor: auth_mode es 'strict' pero no hay CALLBACK_TOKEN.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Servidor no configurado para validar tokens.")

        if not x_authorization or not hmac.compare_digest(auth_token, x_authorization):
            logger.warning(f"Intento de acceso no autorizado. Token recibido: '{str(x_authorization)[:10]}...'")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de autorización inválido o ausente.")

    elif auth_token and x_authorization:
        if not hmac.compare_digest(auth_token, x_authorization):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de autorización inválido.")


# --- Endpoints de la API ---
endpoint_path = cb_config.get("endpoint_path", "/api/callback").strip()
if not endpoint_path.startswith("/"):
    endpoint_path = "/" + endpoint_path


@app.post(
    endpoint_path,
    tags=["Callbacks"],
    summary="Recibe notificaciones de A360",
    response_model=StandardResponse,  # Define el modelo de respuesta para la documentación
    dependencies=[Depends(verify_token)],
)
async def handle_callback(payload: CallbackPayload, request: Request, db: DatabaseConnector = Depends(get_db)):
    """
    Procesa el callback de A360, actualizando el estado en la base de datos.
    """
    try:
        raw_payload = await request.body()
        payload_str = raw_payload.decode("utf-8")

        logger.info(f"Procesando callback para DeploymentId: {payload.deployment_id} con estado: {payload.status}")

        success = db.actualizar_ejecucion_desde_callback(
            deployment_id=payload.deployment_id, estado_callback=payload.status, callback_payload_str=payload_str
        )

        if success:
            return StandardResponse(status="OK", message="Callback procesado exitosamente.")
        else:
            logger.error(f"Error funcional al actualizar la BD para DeploymentId: {payload.deployment_id}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": "ERROR", "message": "Error al actualizar el estado en la base de datos."},
            )

    except Exception as e:
        logger.error(f"Error inesperado procesando el payload: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "ERROR", "message": "Error interno del servidor durante el procesamiento del callback."},
        )


@app.get("/health", tags=["Monitoring"], summary="Verifica el estado del servicio", response_model=StandardResponse)
async def health_check():
    """
    Endpoint simple para verificar que el servicio está en línea.
    """
    return StandardResponse(status="OK", message="Servicio de Callback activo.")
