import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import init_db, AsyncSessionLocal
from config import settings
from routers import devices, heartbeat, commands
from services.alert_service import check_offline_devices


# ──────────────────────────────────────────────
# WebSocket manager — notifica al dashboard en tiempo real
# ──────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(json.dumps(data, default=str))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active.remove(ws)


ws_manager = ConnectionManager()


# ──────────────────────────────────────────────
# Scheduler — worker de detección offline
# ──────────────────────────────────────────────

scheduler = AsyncIOScheduler()

async def offline_check_job():
    async with AsyncSessionLocal() as db:
        await check_offline_devices(db, settings)
    # Notificar al dashboard para que refresque
    await ws_manager.broadcast({"event": "devices_updated"})


# ──────────────────────────────────────────────
# App lifecycle
# ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    scheduler.add_job(offline_check_job, "interval", seconds=60, id="offline_check")
    scheduler.start()
    print(f"✅ TabletMonitor backend iniciado")
    print(f"📋 Docs: http://localhost:8000/docs")
    yield
    # Shutdown
    scheduler.shutdown()


app = FastAPI(
    title="TabletMonitor API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — permite que el dashboard React se conecte
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # En producción: reemplazar con la URL del dashboard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(devices.router)
app.include_router(heartbeat.router)
app.include_router(commands.router)


# ──────────────────────────────────────────────
# WebSocket — dashboard se suscribe aquí
# ──────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        # Mandar estado inicial al conectarse
        await websocket.send_text(json.dumps({"event": "connected", "message": "TabletMonitor WS activo"}))
        while True:
            # Mantener conexión viva — el servidor empuja eventos
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({"event": "ping"}))
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# Hook para broadcast cuando llega un heartbeat
# (lo llaman los routers via dependency injection)
app.state.ws_manager = ws_manager


@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}