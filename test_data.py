import sys
from pathlib import Path

# Ensure the scripts directory is in the python path to import db_tools
scripts_path = str(Path(__file__).resolve().parent / "scripts")
if scripts_path not in sys.path:
    sys.path.append(scripts_path)

# Add src to path for database.py
src_path = str(Path(__file__).resolve().parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

from db_tools import get_db_connector

from sam.web.backend import database as db_service


def test_data():
    db = get_db_connector()
    results = db_service.get_recent_executions(db, limit=5)
    if results["demoras"]:
        for i, item in enumerate(results["demoras"]):
            print(f"Item {i}: Robot={item.get('Robot')}, DeploymentId={item.get('DeploymentId')!r}")
    else:
        print("No demoras found")


if __name__ == "__main__":
    test_data()
