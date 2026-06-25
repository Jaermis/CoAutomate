"""
config.py - Persistent app configuration (SMTP settings, etc.)
Stored as smtp_config.json in the backend directory.
"""
import json
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "smtp_config.json"

DEFAULT_SMTP = {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_username": "",
    "smtp_password": "",
    "smtp_from_name": "CoAutomate System",
}


def load_smtp_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return DEFAULT_SMTP.copy()


def save_smtp_config(config: dict):
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")
