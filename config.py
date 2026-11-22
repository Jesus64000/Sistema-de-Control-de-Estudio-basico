import os
import secrets
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def obtener_secret_key() -> str:
    """Obtiene o genera una SECRET_KEY persistente en .secret_key."""
    env_key = os.getenv("SECRET_KEY")
    if env_key:
        return env_key
    secret_path = os.path.join(BASE_DIR, ".secret_key")
    if os.path.exists(secret_path):
        with open(secret_path, "r", encoding="utf-8") as f:
            key = f.read().strip()
            if key:
                return key
    key = secrets.token_hex(32)
    with open(secret_path, "w", encoding="utf-8") as f:
        f.write(key)
    return key


class Config:
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "los_laureles_ce")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    PORT = int(os.getenv("PORT", "5000"))
    SECRET_KEY = obtener_secret_key()
