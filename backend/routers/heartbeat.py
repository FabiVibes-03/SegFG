from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from database import get_db
from models import Device, DeviceStatus, Heartbeat, Command
from schemas import HeartbeatRequest, HeartbeatResponse
from auth import get_device_from_token
from services.alert_service import evaluate_heartbeat

router = APIRouter(prefix="/api", tags=["heartbeat"])


@router.post("/heartbeat", response_model=HeartbeatResponse)
async def receive_heartbeat(
    body: HeartbeatRequest,
    device: Device = Depends(get_device_from_token),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()

    # 1. Guardar heartbeat
    heartbeat = Heartbeat(
        device_id        = device.id,
        timestamp        = now,
        ip_address       = body.ip_address,
        ssid             = body.ssid,
        mac_address      = body.mac_address,
        battery_level    = body.battery_level,
        battery_charging = body.battery_charging,
        battery_status   = body.battery_status,
        cpu_usage        = body.cpu_usage,
        ram_used_mb      = body.ram_used_mb,
        ram_total_mb     = body.ram_total_mb,
        disk_free_gb     = body.disk_free_gb,
        disk_total_gb    = body.disk_total_gb,
        latitude         = body.latitude,
        longitude        = body.longitude,
        location_accuracy= body.location_accuracy,
        os_version       = body.os_version,
        uptime_seconds   = body.uptime_seconds,
        screen_locked    = body.screen_locked,
        active_user      = body.active_user,
    )
    db.add(heartbeat)

    # 2. Actualizar estado del dispositivo
    was_offline = device.status in (DeviceStatus.OFFLINE, DeviceStatus.LOST, DeviceStatus.WARNING)
    device.status    = DeviceStatus.ONLINE
    device.last_seen = now
    db.add(device)

    # 3. Si vuelve online después de estar offline, crear alerta informativa
    if was_offline:
        from models import Alert, AlertType
        alert = Alert(
            device_id=device.id,
            type=AlertType.BACK_ONLINE,
            message=f"Tablet volvió a estar en línea"
        )
        db.add(alert)

    # 4. Evaluar alertas (red desconocida, batería, geofence)
    await evaluate_heartbeat(db, device.id, body)

    # 5. Buscar comandos pendientes para este dispositivo
    pending_result = await db.execute(
        select(Command).where(
            Command.device_id == device.id,
            Command.executed_at == None,
        ).order_by(Command.created_at)
    )
    pending_commands = pending_result.scalars().all()

    # Marcar como "enviados" (el agente los ejecutará)
    commands_out = []
    for cmd in pending_commands:
        cmd.executed_at = now
        db.add(cmd)
        commands_out.append({
            "id"     : cmd.id,
            "command": cmd.command.value,
            "payload": cmd.payload or {},
        })

    await db.commit()

    return HeartbeatResponse(status="ok", commands=commands_out)