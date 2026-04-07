from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from database import get_db
from models import Command, Alert, AllowedNetwork, Geofence
from schemas import (
    CommandRequest, CommandOut,
    AlertOut,
    AllowedNetworkRequest, AllowedNetworkOut,
    GeofenceRequest, GeofenceOut,
)
from auth import verify_admin_token

router = APIRouter(prefix="/api", tags=["commands"])


# ──────────────────────────────────────────────
# Comandos remotos
# ──────────────────────────────────────────────

@router.post("/devices/{device_id}/command", response_model=CommandOut, dependencies=[Depends(verify_admin_token)])
async def send_command(device_id: str, body: CommandRequest, db: AsyncSession = Depends(get_db)):
    """
    Encola un comando para un dispositivo.
    El agente lo recibirá en el próximo heartbeat (máx 30s de latencia).
    """
    cmd = Command(
        device_id=device_id,
        command=body.command,
        payload=body.payload,
    )
    db.add(cmd)
    await db.commit()
    await db.refresh(cmd)
    return cmd


@router.get("/devices/{device_id}/commands", response_model=list[CommandOut], dependencies=[Depends(verify_admin_token)])
async def list_commands(device_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Command)
        .where(Command.device_id == device_id)
        .order_by(Command.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()


# ──────────────────────────────────────────────
# Alertas
# ──────────────────────────────────────────────

@router.get("/alerts", response_model=list[AlertOut], dependencies=[Depends(verify_admin_token)])
async def list_alerts(only_unread: bool = False, limit: int = 100, db: AsyncSession = Depends(get_db)):
    query = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
    if only_unread:
        query = query.where(Alert.acknowledged == False)
    result = await db.execute(query)
    return result.scalars().all()


@router.patch("/alerts/{alert_id}/acknowledge", dependencies=[Depends(verify_admin_token)])
async def acknowledge_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    alert.acknowledged = True
    alert.acknowledged_at = datetime.utcnow()
    await db.commit()
    return {"ok": True}


@router.patch("/alerts/acknowledge-all", dependencies=[Depends(verify_admin_token)])
async def acknowledge_all_alerts(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import update
    await db.execute(
        Alert.__table__.update()
        .where(Alert.acknowledged == False)
        .values(acknowledged=True, acknowledged_at=datetime.utcnow())
    )
    await db.commit()
    return {"ok": True}


# ──────────────────────────────────────────────
# Redes WiFi autorizadas
# ──────────────────────────────────────────────

@router.get("/networks", response_model=list[AllowedNetworkOut], dependencies=[Depends(verify_admin_token)])
async def list_networks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AllowedNetwork))
    return result.scalars().all()


@router.post("/networks", response_model=AllowedNetworkOut, dependencies=[Depends(verify_admin_token)])
async def add_network(body: AllowedNetworkRequest, db: AsyncSession = Depends(get_db)):
    net = AllowedNetwork(ssid=body.ssid, description=body.description)
    db.add(net)
    await db.commit()
    await db.refresh(net)
    return net


@router.delete("/networks/{network_id}", dependencies=[Depends(verify_admin_token)])
async def delete_network(network_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AllowedNetwork).where(AllowedNetwork.id == network_id))
    net = result.scalars().first()
    if not net:
        raise HTTPException(status_code=404, detail="Red no encontrada")
    await db.delete(net)
    await db.commit()
    return {"ok": True}


# ──────────────────────────────────────────────
# Geofences
# ──────────────────────────────────────────────

@router.get("/geofences", response_model=list[GeofenceOut], dependencies=[Depends(verify_admin_token)])
async def list_geofences(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Geofence))
    return result.scalars().all()


@router.post("/geofences", response_model=GeofenceOut, dependencies=[Depends(verify_admin_token)])
async def create_geofence(body: GeofenceRequest, db: AsyncSession = Depends(get_db)):
    geo = Geofence(**body.model_dump())
    db.add(geo)
    await db.commit()
    await db.refresh(geo)
    return geo


@router.delete("/geofences/{geofence_id}", dependencies=[Depends(verify_admin_token)])
async def delete_geofence(geofence_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Geofence).where(Geofence.id == geofence_id))
    geo = result.scalars().first()
    if not geo:
        raise HTTPException(status_code=404, detail="Geofence no encontrada")
    await db.delete(geo)
    await db.commit()
    return {"ok": True}