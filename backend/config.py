from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Base
    APP_NAME: str = "TabletMonitor"
    DEBUG: bool = False
    SECRET_KEY: str = "CAMBIA_ESTA_CLAVE_EN_PRODUCCION_usa_openssl_rand_hex_32"

    # Base de datos
    # Ejemplos:
    #   Local:      postgresql+asyncpg://user:pass@localhost:5432/tabletmonitor
    #   VPS:        postgresql+asyncpg://user:pass@IP_DEL_VPS:5432/tabletmonitor
    #   SQLite dev: sqlite+aiosqlite:///./tabletmonitor.db
    DATABASE_URL: str = "postgresql+asyncpg://monitor:monitor123@localhost:5432/tabletmonitor"

    # Seguridad
    TOKEN_EXPIRE_DAYS: int = 365          # tokens de dispositivos duran 1 año
    ADMIN_PASSWORD: str = "admin123"      # contraseña del dashboard — CAMBIAR

    # Timeouts para detección de estado
    WARN_AFTER_SECONDS: int = 120         # 2 min sin heartbeat → WARNING
    OFFLINE_AFTER_SECONDS: int = 300      # 5 min → OFFLINE
    LOST_AFTER_SECONDS: int = 600         # 10 min → LOST

    # Heartbeat
    HEARTBEAT_INTERVAL_SECONDS: int = 30  # cada cuánto reporta el agente

    # WiFi — redes autorizadas (se pueden gestionar desde DB también)
    DEFAULT_ALLOWED_SSIDS: list[str] = []

    # Geofencing — radio por defecto en metros (0 = desactivado)
    DEFAULT_GEOFENCE_RADIUS: int = 0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()