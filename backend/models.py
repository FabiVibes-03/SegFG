import uuid
from datetime import datetime
from sqlalchemy import (
    String, Integer, Float, Boolean, Text,
    DateTime, Enum, ForeignKey, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from database import Base


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class DeviceStatus(str, enum.Enum):
    ONLINE  = "online"
    WARNING = "warning"
    OFFLINE = "offline"
    LOST    = "lost"

class AlertType(str, enum.Enum):
    OFFLINE         = "offline"
    UNKNOWN_NETWORK = "unknown_network"
    GEOFENCE        = "geofence"
    LOW_BATTERY     = "low_battery"
    BACK_ONLINE     = "back_online"

class CommandType(str, enum.Enum):
    LOCK     = "lock"
    SHUTDOWN = "shutdown"
    ALARM    = "alarm"       # sonido/alerta visual en la tablet
    MESSAGE  = "message"     # mensaje en pantalla


# ──────────────────────────────────────────────
# Modelos
# ──────────────────────────────────────────────

class Device(Base):
    __tablename__ = "devices"

    id           : Mapped[str]  = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hostname     : Mapped[str]  = mapped_column(String(255))
    mac_address  : Mapped[str]  = mapped_column(String(20), unique=True, index=True)
    api_token    : Mapped[str]  = mapped_column(String(255), unique=True, index=True)
    display_name : Mapped[str]  = mapped_column(String(255), nullable=True)   # nombre amigable
    status       : Mapped[DeviceStatus] = mapped_column(Enum(DeviceStatus), default=DeviceStatus.OFFLINE)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen    : Mapped[datetime] = mapped_column(DateTime, nullable=True)
    notes        : Mapped[str]  = mapped_column(Text, nullable=True)

    heartbeats   : Mapped[list["Heartbeat"]] = relationship(back_populates="device", lazy="dynamic")
    alerts       : Mapped[list["Alert"]]     = relationship(back_populates="device", lazy="dynamic")
    commands     : Mapped[list["Command"]]   = relationship(back_populates="device", lazy="dynamic")


class Heartbeat(Base):
    __tablename__ = "heartbeats"

    id               : Mapped[str]   = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id        : Mapped[str]   = mapped_column(String(36), ForeignKey("devices.id"), index=True)
    timestamp        : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Red
    ip_address       : Mapped[str]   = mapped_column(String(50), nullable=True)
    ssid             : Mapped[str]   = mapped_column(String(255), nullable=True)
    mac_address      : Mapped[str]   = mapped_column(String(20), nullable=True)

    # Batería
    battery_level    : Mapped[int]   = mapped_column(Integer, nullable=True)   # 0-100, None si no hay batería
    battery_charging : Mapped[bool]  = mapped_column(Boolean, nullable=True)
    battery_status   : Mapped[str]   = mapped_column(String(50), nullable=True)

    # Hardware
    cpu_usage        : Mapped[float] = mapped_column(Float, nullable=True)
    ram_used_mb      : Mapped[int]   = mapped_column(Integer, nullable=True)
    ram_total_mb     : Mapped[int]   = mapped_column(Integer, nullable=True)
    disk_free_gb     : Mapped[float] = mapped_column(Float, nullable=True)
    disk_total_gb    : Mapped[float] = mapped_column(Float, nullable=True)

    # Ubicación (GPS — opcional)
    latitude         : Mapped[float] = mapped_column(Float, nullable=True)
    longitude        : Mapped[float] = mapped_column(Float, nullable=True)
    location_accuracy: Mapped[float] = mapped_column(Float, nullable=True)

    # Sistema
    os_version       : Mapped[str]   = mapped_column(String(100), nullable=True)
    uptime_seconds   : Mapped[int]   = mapped_column(Integer, nullable=True)
    screen_locked    : Mapped[bool]  = mapped_column(Boolean, nullable=True)
    active_user      : Mapped[str]   = mapped_column(String(100), nullable=True)

    device: Mapped["Device"] = relationship(back_populates="heartbeats")


class Alert(Base):
    __tablename__ = "alerts"

    id             : Mapped[str]  = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id      : Mapped[str]  = mapped_column(String(36), ForeignKey("devices.id"), index=True)
    type           : Mapped[AlertType] = mapped_column(Enum(AlertType))
    message        : Mapped[str]  = mapped_column(Text)
    created_at     : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    acknowledged   : Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    device: Mapped["Device"] = relationship(back_populates="alerts")


class Command(Base):
    __tablename__ = "commands"

    id          : Mapped[str]  = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id   : Mapped[str]  = mapped_column(String(36), ForeignKey("devices.id"), index=True)
    command     : Mapped[CommandType] = mapped_column(Enum(CommandType))
    payload     : Mapped[dict] = mapped_column(JSON, nullable=True)   # ej: {"message": "Devuelve esta tablet"}
    created_at  : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    executed_at : Mapped[datetime] = mapped_column(DateTime, nullable=True)

    device: Mapped["Device"] = relationship(back_populates="commands")


class AllowedNetwork(Base):
    __tablename__ = "allowed_networks"

    id          : Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ssid        : Mapped[str] = mapped_column(String(255), unique=True)
    description : Mapped[str] = mapped_column(String(255), nullable=True)
    created_at  : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Geofence(Base):
    __tablename__ = "geofences"

    id            : Mapped[str]   = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name          : Mapped[str]   = mapped_column(String(255))
    center_lat    : Mapped[float] = mapped_column(Float)
    center_lng    : Mapped[float] = mapped_column(Float)
    radius_meters : Mapped[int]   = mapped_column(Integer)
    active        : Mapped[bool]  = mapped_column(Boolean, default=True)
    created_at    : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)