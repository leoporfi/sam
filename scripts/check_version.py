import re
import sys
from pathlib import Path


def get_version_from_pyproject():
    try:
        content = Path("pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'version\s*=\s*"([^"]+)"', content)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Error reading pyproject.toml: {e}")
    return None


def get_version_from_init():
    try:
        content = Path("src/sam/__init__.py").read_text(encoding="utf-8")
        match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Error reading src/sam/__init__.py: {e}")
    return None


def main():
    v_toml = get_version_from_pyproject()
    v_init = get_version_from_init()

    if not v_toml:
        print("[ERROR] Could not find version in pyproject.toml")
        sys.exit(1)

    if not v_init:
        print("[ERROR] Could not find version in src/sam/__init__.py")
        sys.exit(1)

    if v_toml != v_init:
        print("[ERROR] Version mismatch!")
        print(f"   pyproject.toml: {v_toml}")
        print(f"   src/sam/__init__.py: {v_init}")
        sys.exit(1)

    print(f"[OK] Versions match: {v_toml}")
    sys.exit(0)


if __name__ == "__main__":
    main()
