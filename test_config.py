import sys
from pathlib import Path

# Add src to path
src_path = str(Path(__file__).resolve().parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from dotenv import load_dotenv

from sam.common.config_manager import ConfigManager

load_dotenv()


def test_config():
    aa_config = ConfigManager.get_aa360_config()
    url = aa_config.get("callback_url_deploy")
    print(f"URL: {url!r}")
    print(f"Type: {type(url)}")


if __name__ == "__main__":
    test_config()
