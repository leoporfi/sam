# src/callback/service/main.py
import hmac
import logging
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Security, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from src.common.database.sql_client import DatabaseConnector
from src.common.utils.config_manager import ConfigManager

# --- Configuración Inicial ---
logger = logging.getLogger(__name__)
# Cargar configuración del servicio de callback
cb_config = ConfigManager.get_callback_server_config()
sql_config = ConfigManager.get_sql_server_config("SQL_SAM")

# --- Definición de Seguridad  ---
api_key_scheme = APIKeyHeader(name="X-Authorization", auto_error=False, description="Clave de API para la autenticación del callback.")


# --- Modelos de Datos (Pydantic) ---
class CallbackPayload(BaseModel):
    deployment_id: str = Field(..., alias="deploymentId", description="Identificador único del deployment.")
    status: str = Field(..., description="Estado de la ejecución (ej. COMPLETED, FAILED).")
    device_id: Optional[str] = Field(None, alias="deviceId", description="(Opcional) Identificador del dispositivo que ejecutó el bot.")
    user_id: Optional[str] = Field(None, alias="userId", description="(Opcional) Identificador del usuario asociado a la ejecución.")
    bot_output: Optional[Dict[str, Any]] = Field(None, alias="botOutput", description="(Opcional) Salida generada por el bot.")


class SuccessResponse(BaseModel):
    """
    Define el formato de respuesta JSON estándar para toda la API.
    """

    status: str = "OK"
    message: str


class ErrorResponse(BaseModel):
    status: str = "ERROR"
    message: str


# --- Inicialización de la Aplicación FastAPI ---
app = FastAPI(
    title="SAM Callback Service API",
    version="2.3.0",
    description="""
API para recibir callbacks desde Control Room a través del API Gateway.
**Requiere obligatoriamente una Clave de API en el header `X-Authorization`.**
    """,
    servers=[
        {"url": "http://10.167.181.41:8008", "description": "Servidor de Producción"},
        {"url": "http://10.167.181.42:8008", "description": "Servidor de Desarrollo"},
    ],
)

db_connector: Optional[DatabaseConnector] = None


# --- Ciclo de Vida de la Aplicación (Startup/Shutdown) ---
@app.on_event("startup")
def startup_event():
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
    if db_connector:
        logger.info("Cerrando la conexión de la base de datos.")
        db_connector.cerrar_conexion()


# --- Manejadores de Excepciones Personalizados ---
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Captura las excepciones HTTP y formatea la respuesta para que coincida con el formato estándar.
    """
    return JSONResponse(status_code=exc.status_code, content={"status": "ERROR", "message": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Captura los errores de validación de Pydantic y los formatea.
    """
    error_message = exc.errors()[0]["msg"] if exc.errors() else "Error de validación en la petición"
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"status": "ERROR", "message": f"Petición inválida: {error_message}"})


# --- Dependencias de FastAPI ---
def get_db() -> DatabaseConnector:
    """
    Dependencia de FastAPI para obtener el conector de base de datos.
    """
    if not db_connector:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="La conexión con la base de datos no está disponible.")
    return db_connector


async def verify_api_key(x_authorization: Optional[str] = Header(None, alias="X-Authorization")):
    """
    Dependencia de seguridad para validar la Clave de API (API Key).
    Respeta el CALLBACK_AUTH_MODE ('strict' u 'optional').
    """
    auth_mode = cb_config.get("auth_mode", "strict")

    # En modo opcional, si no se provee el header, se permite el acceso.
    if auth_mode == "optional" and x_authorization is None:
        logger.debug("Acceso permitido sin API Key en modo 'optional'.")
        return

    # Si estamos en modo 'strict' o si la API Key fue provista en modo 'optional',
    # se debe realizar la validación.
    server_api_key = cb_config.get("callback_api_key")

    if not server_api_key:
        logger.error("Error de configuración del servidor: No se ha definido un CALLBACK_API_KEY para validar.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Servidor no configurado para validar claves de API.")

    if not x_authorization or not hmac.compare_digest(server_api_key, x_authorization):
        logger.warning(f"Intento de acceso no autorizado. API Key recibida: '{str(x_authorization)[:10]}...'")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Clave de API inválida o ausente.")


# --- Endpoints de la API ---
endpoint_path = cb_config.get("endpoint_path", "/api/callback").strip()
if not endpoint_path.startswith("/"):
    endpoint_path = "/" + endpoint_path


@app.post(
    endpoint_path,
    tags=["Callback"],
    summary="Recibir notificación de callback de A360",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Callback procesado correctamente.", "model": SuccessResponse},
        400: {"description": "Petición inválida (JSON malformado o faltan campos requeridos).", "model": ErrorResponse},
        401: {
            "description": "Autenticación Fallida. La Clave de API en 'X-Authorization' es inválida o no fue proporcionada.",
            "model": ErrorResponse,
        },
        500: {"description": "Error interno del servidor.", "model": ErrorResponse},
    },
    dependencies=[Depends(verify_api_key)],
)
async def handle_callback(payload: CallbackPayload, request: Request, db: DatabaseConnector = Depends(get_db)):
    """
    Procesa el callback de A360, actualizando el estado en la base de datos.
    """
    try:
        raw_payload = await request.body()
        payload_str = raw_payload.decode("utf-8")
        logger.info(f"Callback recibido para DeploymentId: {payload.deployment_id}. Body: {payload_str}")

        success = db.actualizar_ejecucion_desde_callback(
            deployment_id=payload.deployment_id, estado_callback=payload.status, callback_payload_str=payload_str
        )

        if success:
            return SuccessResponse(message="Callback procesado correctamente.")
        else:
            logger.error(f"Error funcional al actualizar la BD para DeploymentId: {payload.deployment_id}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al actualizar el estado en la base de datos.")

    except HTTPException as http_exc:
        raise http_exc  # Re-lanzar excepciones HTTP ya manejadas
    except Exception as e:
        logger.error(f"Error inesperado procesando el payload: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor durante el procesamiento del callback."
        )


@app.get("/health", tags=["Monitoring"], summary="Verifica el estado del servicio", response_model=SuccessResponse)
async def health_check():
    """
    Endpoint simple para verificar que el servicio está en línea.
    """
    return SuccessResponse(message="Servicio de Callback activo.")
