from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from database import get_db
from models import Device, DeviceStatus, Heartbeat
from schemas import (
    DeviceRegisterRequest, DeviceRegisterResponse,
    DeviceOut, AdminLoginRequest, AdminLoginResponse, DashboardSummary
)
from auth import generate_device_token, verify_admin_token, create_admin_token
from config import settings

router = APIRouter(prefix="/api", tags=["devices"])


# ──────────────────────────────────────────────
# Auth admin
# ──────────────────────────────────────────────

@router.post("/admin/login", response_model=AdminLoginResponse)
async def admin_login(body: AdminLoginRequest):
    if body.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    return AdminLoginResponse(access_token=create_admin_token())


# ──────────────────────────────────────────────
# Registro de dispositivos
# ──────────────────────────────────────────────

@router.post("/register", response_model=DeviceRegisterResponse)
async def register_device(body: DeviceRegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    El agente llama esto una sola vez al instalarse.
    Si el dispositivo ya existe (misma MAC), renueva el token.
    """
    result = await db.execute(select(Device).where(Device.mac_address == body.mac_address))
    existing = result.scalars().first()

    token_plain, token_hash = generate_device_token()

    if existing:
        # Dispositivo conocido — renovar token
        existing.api_token = token_hash
        existing.hostname = body.hostname
        await db.commit()
        return DeviceRegisterResponse(
            device_id=existing.id,
            api_token=token_plain,
            message="Dispositivo re-registrado, token renovado"
        )

    # Nuevo dispositivo
    device = Device(
        hostname=body.hostname,
        mac_address=body.mac_address,
        api_token=token_hash,
        display_name=body.hostname,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)

    return DeviceRegisterResponse(device_id=device.id, api_token=token_plain)


# ──────────────────────────────────────────────
# Listado y detalle (requieren auth admin)
# ──────────────────────────────────────────────

@router.get("/devices", response_model=list[DeviceOut], dependencies=[Depends(verify_admin_token)])
async def list_devices(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Device).order_by(Device.last_seen.desc()))
    return result.scalars().all()


@router.get("/devices/{device_id}", response_model=DeviceOut, dependencies=[Depends(verify_admin_token)])
async def get_device(device_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalars().first()
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    return device


@router.patch("/devices/{device_id}", dependencies=[Depends(verify_admin_token)])
async def update_device(device_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Permite actualizar display_name y notes desde el dashboard."""
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalars().first()
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    if "display_name" in body:
        device.display_name = body["display_name"]
    if "notes" in body:
        device.notes = body["notes"]

    await db.commit()
    return {"ok": True}


@router.get("/devices/{device_id}/history", dependencies=[Depends(verify_admin_token)])
async def device_history(device_id: str, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Últimos N heartbeats de un dispositivo."""
    result = await db.execute(
        select(Heartbeat)
        .where(Heartbeat.device_id == device_id)
        .order_by(Heartbeat.timestamp.desc())
        .limit(limit)
    )
    heartbeats = result.scalars().all()
    return [
        {
            "timestamp"       : h.timestamp,
            "battery_level"   : h.battery_level,
            "battery_charging": h.battery_charging,
            "cpu_usage"       : h.cpu_usage,
            "ram_used_mb"     : h.ram_used_mb,
            "ram_total_mb"    : h.ram_total_mb,
            "ip_address"      : h.ip_address,
            "ssid"            : h.ssid,
            "latitude"        : h.latitude,
            "longitude"       : h.longitude,
        }
        for h in heartbeats
    ]


# ──────────────────────────────────────────────
# Dashboard summary
# ──────────────────────────────────────────────

@router.get("/summary", response_model=DashboardSummary, dependencies=[Depends(verify_admin_token)])
async def get_summary(db: AsyncSession = Depends(get_db)):
    from models import Alert

    devices_result = await db.execute(select(Device))
    devices = devices_result.scalars().all()

    alerts_result = await db.execute(
        select(func.count()).select_from(Alert).where(Alert.acknowledged == False)
    )
    unread = alerts_result.scalar()

    status_counts = {s: 0 for s in DeviceStatus}
    for d in devices:
        status_counts[d.status] += 1

    return DashboardSummary(
        total_devices=len(devices),
        online=status_counts[DeviceStatus.ONLINE],
        warning=status_counts[DeviceStatus.WARNING],
        offline=status_counts[DeviceStatus.OFFLINE],
        lost=status_counts[DeviceStatus.LOST],
        unread_alerts=unread,
    )