import asyncio
import os

from sam.common.config_loader import ConfigLoader
from sam.common.config_manager import ConfigManager
from sam.common.database import DatabaseConnector


async def verify_precedence():
    # 0. Initialize ConfigLoader to load .env
    ConfigLoader.initialize_service("test")

    # 1. Setup DB connector
    sql_config = ConfigManager.get_sql_server_config("SQL_SAM")
    db = DatabaseConnector(
        servidor=sql_config["servidor"],
        base_datos=sql_config["base_datos"],
        usuario=sql_config["usuario"],
        contrasena=sql_config["contrasena"],
        db_config_prefix="SQL_SAM",
    )
    ConfigManager.set_db_connector(db)

    # 2. Set an ENV var
    os.environ["TEST_CONFIG_KEY"] = "env_value"

    # 3. Check value (should be env_value since not in DB)
    val1 = ConfigManager._get_config_value("TEST_CONFIG_KEY")
    print(f"Value from ENV: {val1}")

    # 4. Insert into DB
    db.ejecutar_consulta(
        "IF NOT EXISTS (SELECT 1 FROM dbo.ConfiguracionSistema WHERE Clave = 'TEST_CONFIG_KEY') "
        "INSERT INTO dbo.ConfiguracionSistema (Clave, Valor, Descripcion) VALUES ('TEST_CONFIG_KEY', 'db_value', 'Test')",
        es_select=False,
    )

    # 5. Clear cache to force reload
    ConfigManager._config_cache = {}
    ConfigManager._last_cache_update = 0

    # 6. Check value (should be db_value)
    val2 = ConfigManager._get_config_value("TEST_CONFIG_KEY")
    print(f"Value from DB: {val2}")

    # 7. Cleanup
    db.ejecutar_consulta("DELETE FROM dbo.ConfiguracionSistema WHERE Clave = 'TEST_CONFIG_KEY'", es_select=False)

    if val2 == "db_value":
        print("VERIFICATION SUCCESS: DB takes precedence over ENV")
    else:
        print("VERIFICATION FAILED: DB does not take precedence")


if __name__ == "__main__":
    asyncio.run(verify_precedence())
