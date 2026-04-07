import math
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from models import Alert, AlertType, AllowedNetwork, Geofence, Device, DeviceStatus
from schemas import HeartbeatRequest


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula distancia en metros entre dos coordenadas GPS."""
    R = 6371000  # radio de la Tierra en metros
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def _already_alerted(db: AsyncSession, device_id: str, alert_type: AlertType) -> bool:
    """Evita crear alertas duplicadas del mismo tipo si ya hay una sin reconocer."""
    result = await db.execute(
        select(Alert).where(
            and_(
                Alert.device_id == device_id,
                Alert.type == alert_type,
                Alert.acknowledged == False,
            )
        )
    )
    return result.scalars().first() is not None


async def _create_alert(db: AsyncSession, device_id: str, alert_type: AlertType, message: str):
    if not await _already_alerted(db, device_id, alert_type):
        alert = Alert(device_id=device_id, type=alert_type, message=message)
        db.add(alert)


async def evaluate_heartbeat(db: AsyncSession, device_id: str, data: HeartbeatRequest):
    """
    Evalúa un heartbeat recibido y genera alertas si corresponde.
    Se llama cada vez que llega un heartbeat.
    """

    # 1. Red desconocida
    if data.ssid:
        networks_result = await db.execute(select(AllowedNetwork))
        allowed = [n.ssid for n in networks_result.scalars().all()]

        if allowed and data.ssid not in allowed:
            await _create_alert(
                db, device_id, AlertType.UNKNOWN_NETWORK,
                f"Tablet conectada a red desconocida: '{data.ssid}'"
            )

    # 2. Batería crítica (menos de 10%)
    if data.battery_level is not None and data.battery_level < 10 and not data.battery_charging:
        await _create_alert(
            db, device_id, AlertType.LOW_BATTERY,
            f"Batería crítica: {data.battery_level}%"
        )

    # 3. Geofencing (si hay GPS y hay zonas definidas)
    if data.latitude is not None and data.longitude is not None:
        geofences_result = await db.execute(
            select(Geofence).where(Geofence.active == True)
        )
        geofences = geofences_result.scalars().all()

        if geofences:
            # Si hay zonas, el dispositivo debe estar DENTRO de al menos una
            inside_any = any(
                haversine_distance(data.latitude, data.longitude, g.center_lat, g.center_lng) <= g.radius_meters
                for g in geofences
            )
            if not inside_any:
                await _create_alert(
                    db, device_id, AlertType.GEOFENCE,
                    f"Tablet fuera de zona autorizada — coordenadas: {data.latitude:.5f}, {data.longitude:.5f}"
                )


async def check_offline_devices(db: AsyncSession, settings):
    """
    Worker que corre periódicamente para detectar tablets sin heartbeat.
    Se llama desde APScheduler cada 60 segundos.
    """
    from sqlalchemy import update

    now = datetime.utcnow()
    devices_result = await db.execute(select(Device))
    devices = devices_result.scalars().all()

    for device in devices:
        if device.last_seen is None:
            continue

        elapsed = (now - device.last_seen).total_seconds()
        old_status = device.status

        # Determinar nuevo status
        if elapsed >= settings.LOST_AFTER_SECONDS:
            new_status = DeviceStatus.LOST
        elif elapsed >= settings.OFFLINE_AFTER_SECONDS:
            new_status = DeviceStatus.OFFLINE
        elif elapsed >= settings.WARN_AFTER_SECONDS:
            new_status = DeviceStatus.WARNING
        else:
            new_status = DeviceStatus.ONLINE

        # Actualizar si cambió
        if new_status != old_status:
            device.status = new_status
            db.add(device)

            # Generar alerta solo al pasar a OFFLINE o LOST
            if new_status in (DeviceStatus.OFFLINE, DeviceStatus.LOST):
                await _create_alert(
                    db, device.id, AlertType.OFFLINE,
                    f"Tablet sin respuesta hace {int(elapsed // 60)} minutos (estado: {new_status.value})"
                )

    await db.commit()