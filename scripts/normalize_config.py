import logging

from sam.common.config_manager import ConfigManager
from sam.common.database import DatabaseConnector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def normalize_db_config():
    try:
        sql_config = ConfigManager.get_sql_server_config("SQL_SAM")
        db = DatabaseConnector(
            servidor=sql_config["servidor"],
            base_datos=sql_config["base_datos"],
            usuario=sql_config["usuario"],
            contrasena=sql_config["contrasena"],
            db_config_prefix="SQL_SAM",
        )

        logger.info("Normalizando valores booleanos en ConfiguracionSistema...")

        # Normalizar a 'True'
        res_true = db.ejecutar_consulta(
            "UPDATE dbo.ConfiguracionSistema SET Valor = 'True' WHERE Valor IN ('true', '1', 'TRUE')", es_select=False
        )

        # Normalizar a 'False'
        res_false = db.ejecutar_consulta(
            "UPDATE dbo.ConfiguracionSistema SET Valor = 'False' WHERE Valor IN ('false', '0', 'FALSE')",
            es_select=False,
        )

        logger.info(f"Normalización completada. {res_true} valores actualizados a 'True', {res_false} a 'False'.")

    except Exception as e:
        logger.error(f"Error durante la normalización: {e}")


if __name__ == "__main__":
    normalize_db_config()
