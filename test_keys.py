import asyncio
import sys
from pathlib import Path

# Add src to path
src_path = str(Path(__file__).resolve().parent.parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from sam.common.config_manager import ConfigManager
from sam.common.database import DatabaseConnector
from sam.web.backend import database as db_service


async def test_keys():
    cfg_sql_sam = ConfigManager.get_sql_server_config("SQL_SAM")
    db = DatabaseConnector(
        servidor=cfg_sql_sam["servidor"],
        base_datos=cfg_sql_sam["base_datos"],
        usuario=cfg_sql_sam["usuario"],
        contrasena=cfg_sql_sam["contrasena"],
    )

    results = db_service.get_recent_executions(db, limit=1)
    if results["demoras"]:
        print("Keys in demoras:", results["demoras"][0].keys())
        print("Sample item:", results["demoras"][0])
    else:
        print("No demoras found")


if __name__ == "__main__":
    asyncio.run(test_keys())
