from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from models import DeviceStatus, AlertType, CommandType


# ──────────────────────────────────────────────
# Dispositivos
# ──────────────────────────────────────────────

class DeviceRegisterRequest(BaseModel):
    hostname    : str
    mac_address : str
    os_version  : Optional[str] = None

class DeviceRegisterResponse(BaseModel):
    device_id   : str
    api_token   : str
    message     : str = "Dispositivo registrado correctamente"

class DeviceOut(BaseModel):
    id           : str
    hostname     : str
    mac_address  : str
    display_name : Optional[str]
    status       : DeviceStatus
    registered_at: datetime
    last_seen    : Optional[datetime]
    notes        : Optional[str]

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Heartbeat
# ──────────────────────────────────────────────

class HeartbeatRequest(BaseModel):
    # Red
    ip_address       : Optional[str]   = None
    ssid             : Optional[str]   = None
    mac_address      : Optional[str]   = None

    # Batería
    battery_level    : Optional[int]   = Field(None, ge=0, le=100)
    battery_charging : Optional[bool]  = None
    battery_status   : Optional[str]   = None

    # Hardware
    cpu_usage        : Optional[float] = Field(None, ge=0, le=100)
    ram_used_mb      : Optional[int]   = None
    ram_total_mb     : Optional[int]   = None
    disk_free_gb     : Optional[float] = None
    disk_total_gb    : Optional[float] = None

    # GPS
    latitude         : Optional[float] = None
    longitude        : Optional[float] = None
    location_accuracy: Optional[float] = None

    # Sistema
    os_version       : Optional[str]   = None
    uptime_seconds   : Optional[int]   = None
    screen_locked    : Optional[bool]  = None
    active_user      : Optional[str]   = None

class HeartbeatResponse(BaseModel):
    status   : str = "ok"
    commands : list[dict] = []     # comandos pendientes a ejecutar


# ──────────────────────────────────────────────
# Alertas
# ──────────────────────────────────────────────

class AlertOut(BaseModel):
    id             : str
    device_id      : str
    type           : AlertType
    message        : str
    created_at     : datetime
    acknowledged   : bool
    acknowledged_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Comandos
# ──────────────────────────────────────────────

class CommandRequest(BaseModel):
    command : CommandType
    payload : Optional[dict] = None

class CommandOut(BaseModel):
    id         : str
    device_id  : str
    command    : CommandType
    payload    : Optional[dict]
    created_at : datetime
    executed_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Redes y geofences
# ──────────────────────────────────────────────

class AllowedNetworkRequest(BaseModel):
    ssid       : str
    description: Optional[str] = None

class AllowedNetworkOut(BaseModel):
    id         : str
    ssid       : str
    description: Optional[str]
    created_at : datetime

    model_config = {"from_attributes": True}

class GeofenceRequest(BaseModel):
    name          : str
    center_lat    : float
    center_lng    : float
    radius_meters : int = Field(..., gt=0)

class GeofenceOut(BaseModel):
    id            : str
    name          : str
    center_lat    : float
    center_lng    : float
    radius_meters : int
    active        : bool
    created_at    : datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Auth (admin dashboard)
# ──────────────────────────────────────────────

class AdminLoginRequest(BaseModel):
    password: str

class AdminLoginResponse(BaseModel):
    access_token: str
    token_type  : str = "bearer"


# ──────────────────────────────────────────────
# Dashboard summary
# ──────────────────────────────────────────────

class DashboardSummary(BaseModel):
    total_devices  : int
    online         : int
    warning        : int
    offline        : int
    lost           : int
    unread_alerts  : int