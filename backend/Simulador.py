"""
TabletMonitor — Simulador de Tablets
=====================================
Simula entre 1 y 10 tablets enviando heartbeats reales al backend.
Cubre todos los escenarios posibles para probar el sistema completo.

Uso:
    python simulator.py                    # menú interactivo
    python simulator.py --url http://IP:8000

Requiere:
    pip install httpx rich --break-system-packages
"""

import asyncio
import httpx
import random
import argparse
import math
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()

# ──────────────────────────────────────────────────────────
# Configuración del simulador
# ──────────────────────────────────────────────────────────

DEFAULT_URL = "http://localhost:8000"

# Escenarios predefinidos para cada tablet simulada
SCENARIOS = [
    {
        "name":    "Tablet-01 (Normal)",
        "mac":     "AA:BB:CC:DD:EE:01",
        "mode":    "normal",           # heartbeat normal y estable
        "ssid":    "OficinaWiFi",
        "battery": 85,
    },
    {
        "name":    "Tablet-02 (Batería baja)",
        "mac":     "AA:BB:CC:DD:EE:02",
        "mode":    "low_battery",      # batería bajando hasta critica
        "ssid":    "OficinaWiFi",
        "battery": 12,
    },
    {
        "name":    "Tablet-03 (Red desconocida)",
        "mac":     "AA:BB:CC:DD:EE:03",
        "mode":    "unknown_network",  # se conecta a red no autorizada
        "ssid":    "iPhone_de_Juan",   # red no en lista blanca
        "battery": 70,
    },
    {
        "name":    "Tablet-04 (GPS fuera de zona)",
        "mac":     "AA:BB:CC:DD:EE:04",
        "mode":    "geofence",         # coordenadas fuera del geofence
        "ssid":    "OficinaWiFi",
        "battery": 55,
        "lat":     19.432,             # fuera de zona (si geofence está en otro lado)
        "lng":     -99.133,
    },
    {
        "name":    "Tablet-05 (Se desconecta)",
        "mac":     "AA:BB:CC:DD:EE:05",
        "mode":    "goes_offline",     # envía heartbeats y luego desaparece
        "ssid":    "OficinaWiFi",
        "battery": 40,
    },
    {
        "name":    "Tablet-06 (CPU alta)",
        "mac":     "AA:BB:CC:DD:EE:06",
        "mode":    "high_cpu",         # CPU al 90-100%
        "ssid":    "OficinaWiFi",
        "battery": 60,
    },
    {
        "name":    "Tablet-07 (Cargando)",
        "mac":     "AA:BB:CC:DD:EE:07",
        "mode":    "charging",         # batería subiendo (está conectada)
        "ssid":    "OficinaWiFi",
        "battery": 30,
    },
    {
        "name":    "Tablet-08 (Pantalla bloqueada)",
        "mac":     "AA:BB:CC:DD:EE:08",
        "mode":    "locked",           # siempre con pantalla bloqueada
        "ssid":    "OficinaWiFi",
        "battery": 90,
    },
    {
        "name":    "Tablet-09 (Itinerante)",
        "mac":     "AA:BB:CC:DD:EE:09",
        "mode":    "roaming",          # cambia de red frecuentemente
        "ssid":    "OficinaWiFi",
        "battery": 50,
    },
    {
        "name":    "Tablet-10 (Sin GPS)",
        "mac":     "AA:BB:CC:DD:EE:10",
        "mode":    "no_gps",           # todo normal pero sin GPS
        "ssid":    "OficinaWiFi",
        "battery": 75,
    },
]

SSID_POOL = ["OficinaWiFi", "iPhone_de_Juan", "Vecino_5G", "INFINITUM_ABC", "OficinaWiFi_5G"]


# ──────────────────────────────────────────────────────────
# Clase Tablet simulada
# ──────────────────────────────────────────────────────────

class SimulatedTablet:
    def __init__(self, scenario: dict, server_url: str):
        self.name       = scenario["name"]
        self.mac        = scenario["mac"]
        self.mode       = scenario["mode"]
        self.ssid       = scenario["ssid"]
        self.battery    = scenario["battery"]
        self.lat        = scenario.get("lat")
        self.lng        = scenario.get("lng")
        self.server_url = server_url

        self.token      = None
        self.device_id  = None
        self.tick       = 0
        self.status     = "registrando..."
        self.last_cmd   = None
        self.offline    = False
        self.cpu        = random.uniform(10, 40)
        self.ram_used   = random.randint(1500, 3000)
        self.uptime     = random.randint(3600, 86400)

    async def register(self, client: httpx.AsyncClient) -> bool:
        try:
            res = await client.post(f"{self.server_url}/api/register", json={
                "hostname":   self.name.replace(" ", "-").replace("(", "").replace(")", ""),
                "mac_address": self.mac,
                "os_version": "Windows 11 Pro 22H2",
            }, timeout=10)
            if res.status_code == 200:
                data        = res.json()
                self.token  = data["api_token"]
                self.device_id = data["device_id"]
                self.status = "✓ registrada"
                return True
            else:
                self.status = f"error registro: {res.status_code}"
                return False
        except Exception as e:
            self.status = f"sin conexión: {e}"
            return False

    def _build_payload(self) -> dict:
        """Construye el payload según el modo/escenario."""
        self.tick    += 1
        self.uptime  += 30
        self.cpu      = max(2, min(100, self.cpu + random.uniform(-8, 8)))

        payload = {
            "ip_address":      f"192.168.1.{10 + int(self.mac[-2:], 16) % 200}",
            "ssid":            self.ssid,
            "mac_address":     self.mac,
            "cpu_usage":       round(self.cpu, 1),
            "ram_used_mb":     self.ram_used + random.randint(-100, 100),
            "ram_total_mb":    8192,
            "disk_free_gb":    round(random.uniform(20, 120), 1),
            "disk_total_gb":   256.0,
            "os_version":      "Windows 11 Pro 22H2",
            "uptime_seconds":  self.uptime,
            "screen_locked":   False,
            "active_user":     "usuario",
        }

        # ── Escenarios específicos ──

        if self.mode == "normal":
            self.battery = max(5, self.battery - random.uniform(0, 0.3))
            payload["battery_level"]    = int(self.battery)
            payload["battery_charging"] = False

        elif self.mode == "low_battery":
            # Batería bajando — después de tick 5 entra en zona crítica
            self.battery = max(1, self.battery - random.uniform(1, 2))
            payload["battery_level"]    = int(self.battery)
            payload["battery_charging"] = False

        elif self.mode == "unknown_network":
            # Alterna entre red conocida y desconocida cada 3 ticks
            if self.tick % 6 < 3:
                payload["ssid"] = "OficinaWiFi"
                self.status = "🟡 red conocida"
            else:
                payload["ssid"] = "iPhone_de_Juan"
                self.status = "🔴 red desconocida!"
            payload["battery_level"]    = 70
            payload["battery_charging"] = False

        elif self.mode == "geofence":
            # GPS fuera de zona — coordenadas fijas lejos del centro
            payload["latitude"]          = self.lat + random.uniform(-0.001, 0.001)
            payload["longitude"]         = self.lng + random.uniform(-0.001, 0.001)
            payload["location_accuracy"] = 15.0
            payload["battery_level"]     = int(self.battery)
            payload["battery_charging"]  = False
            self.status = f"📍 GPS: {self.lat:.3f},{self.lng:.3f}"

        elif self.mode == "goes_offline":
            # Envía 5 heartbeats y luego se desconecta por 2 min
            if self.tick <= 5:
                payload["battery_level"]    = int(self.battery)
                payload["battery_charging"] = False
                self.status = f"🟢 tick {self.tick}/5"
            else:
                self.offline = True
                self.status  = "💀 desconectada (esperando detección)"

        elif self.mode == "high_cpu":
            self.cpu = random.uniform(85, 100)
            payload["cpu_usage"]        = round(self.cpu, 1)
            payload["battery_level"]    = int(self.battery)
            payload["battery_charging"] = False
            self.status = f"🔥 CPU: {self.cpu:.0f}%"

        elif self.mode == "charging":
            # Batería subiendo
            self.battery = min(100, self.battery + random.uniform(0.5, 1.5))
            payload["battery_level"]    = int(self.battery)
            payload["battery_charging"] = True
            self.status = f"⚡ cargando {int(self.battery)}%"

        elif self.mode == "locked":
            payload["screen_locked"]    = True
            payload["battery_level"]    = int(self.battery)
            payload["battery_charging"] = False
            payload["active_user"]      = "SYSTEM"
            self.status = "🔒 pantalla bloqueada"

        elif self.mode == "roaming":
            # Cambia de SSID cada tick
            payload["ssid"]             = random.choice(SSID_POOL)
            payload["battery_level"]    = int(self.battery)
            payload["battery_charging"] = False
            self.status = f"📶 ssid: {payload['ssid']}"

        elif self.mode == "no_gps":
            # Sin GPS — sin lat/lng en payload
            payload["battery_level"]    = int(self.battery)
            payload["battery_charging"] = False

        return payload

    async def run_tick(self, client: httpx.AsyncClient):
        if self.offline or not self.token:
            return

        payload = self._build_payload()
        if self.offline:
            return

        try:
            res = await client.post(
                f"{self.server_url}/api/heartbeat",
                json=payload,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=8,
            )
            if res.status_code == 200:
                data     = res.json()
                commands = data.get("commands", [])
                if commands:
                    self.last_cmd = commands[-1]["command"]
                    self.status   = f"⚡ CMD: {self.last_cmd}"
                elif self.status.startswith("⚡ CMD"):
                    self.status = "✓ ok"
                elif self.mode == "normal":
                    self.status = f"✓ bat:{int(self.battery)}%"
            else:
                self.status = f"err {res.status_code}"
        except Exception as e:
            self.status = f"⚠ {str(e)[:30]}"


# ──────────────────────────────────────────────────────────
# Setup inicial — crear red autorizada en el backend
# ──────────────────────────────────────────────────────────

async def setup_backend(server_url: str, admin_password: str):
    """Crea las redes autorizadas necesarias para que los escenarios funcionen."""
    async with httpx.AsyncClient() as client:
        # Login
        res = await client.post(f"{server_url}/api/admin/login",
                                json={"password": admin_password}, timeout=8)
        if res.status_code != 200:
            console.print(f"[red]Login admin falló ({res.status_code}). Verifica ADMIN_PASSWORD en .env[/red]")
            return None
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Agregar "OficinaWiFi" como red autorizada
        try:
            await client.post(f"{server_url}/api/networks",
                              json={"ssid": "OficinaWiFi", "description": "Red principal de oficina"},
                              headers=headers, timeout=8)
            await client.post(f"{server_url}/api/networks",
                              json={"ssid": "OficinaWiFi_5G", "description": "Red 5GHz oficina"},
                              headers=headers, timeout=8)
            console.print("[green]✓ Redes autorizadas configuradas: OficinaWiFi, OficinaWiFi_5G[/green]")
        except Exception as e:
            console.print(f"[yellow]Redes ya existen o error: {e}[/yellow]")

        # Crear geofence en CDMX (para que Tablet-04 quede fuera)
        try:
            await client.post(f"{server_url}/api/geofences", json={
                "name": "Oficina Central",
                "center_lat": 20.9674,
                "center_lng": -89.6235,
                "radius_meters": 500,
            }, headers=headers, timeout=8)
            console.print("[green]✓ Geofence creado: Oficina Central (radio 500m)[/green]")
        except Exception as e:
            console.print(f"[yellow]Geofence ya existe o error: {e}[/yellow]")

        console.print()
        return token


# ──────────────────────────────────────────────────────────
# Tabla en tiempo real (Rich Live)
# ──────────────────────────────────────────────────────────

def build_table(tablets: list[SimulatedTablet], tick: int, elapsed: int) -> Panel:
    table = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        padding=(0, 1),
    )
    table.add_column("Tablet",    style="white",       min_width=28)
    table.add_column("Modo",      style="dim",         min_width=18)
    table.add_column("Estado",    min_width=32)
    table.add_column("Tick",      style="dim",         justify="right", min_width=5)
    table.add_column("Último CMD",style="yellow",      min_width=12)

    for t in tablets:
        status_text = Text(t.status)
        if "error" in t.status or "err" in t.status:
            status_text.stylize("red")
        elif "✓" in t.status:
            status_text.stylize("green")
        elif "💀" in t.status or "desconect" in t.status:
            status_text.stylize("red")
        elif "⚠" in t.status:
            status_text.stylize("yellow")

        table.add_row(
            t.name,
            t.mode,
            status_text,
            str(t.tick),
            t.last_cmd or "—",
        )

    mins = elapsed // 60
    secs = elapsed % 60
    title = f"[bold]TabletMonitor Simulator[/bold] — tick #{tick}  |  tiempo: {mins:02d}:{secs:02d}  |  [dim]Ctrl+C para detener[/dim]"
    return Panel(table, title=title, border_style="blue")


# ──────────────────────────────────────────────────────────
# Loop principal
# ──────────────────────────────────────────────────────────

async def run_simulator(server_url: str, num_tablets: int, interval: int, admin_password: str):
    console.print(f"\n[bold blue]TabletMonitor Simulator[/bold blue]")
    console.print(f"Servidor: [cyan]{server_url}[/cyan]")
    console.print(f"Tablets:  [cyan]{num_tablets}[/cyan]")
    console.print(f"Intervalo:[cyan]{interval}s[/cyan]\n")

    # Setup inicial
    console.print("[yellow]Configurando backend...[/yellow]")
    await setup_backend(server_url, admin_password)

    # Crear tablets
    scenarios = SCENARIOS[:num_tablets]
    tablets   = [SimulatedTablet(s, server_url) for s in scenarios]

    # Registrar todas
    console.print("[yellow]Registrando tablets...[/yellow]")
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[t.register(client) for t in tablets])

    ok = sum(results)
    console.print(f"[green]✓ {ok}/{len(tablets)} tablets registradas[/green]\n")

    if ok == 0:
        console.print("[red]No se pudo registrar ninguna tablet. ¿El servidor está corriendo?[/red]")
        return

    # Loop de heartbeats con tabla en vivo
    tick    = 0
    start   = asyncio.get_event_loop().time()

    with Live(console=console, refresh_per_second=2) as live:
        async with httpx.AsyncClient() as client:
            while True:
                tick    += 1
                elapsed  = int(asyncio.get_event_loop().time() - start)

                # Enviar heartbeats en paralelo
                await asyncio.gather(*[t.run_tick(client) for t in tablets])

                # Actualizar tabla
                live.update(build_table(tablets, tick, elapsed))

                await asyncio.sleep(interval)


# ──────────────────────────────────────────────────────────
# Menú interactivo
# ──────────────────────────────────────────────────────────

def interactive_menu() -> tuple[str, int, int, str]:
    console.print(Panel.fit(
        "[bold blue]TabletMonitor — Simulador de Pruebas[/bold blue]\n"
        "[dim]Simula tablets reales enviando heartbeats al backend[/dim]",
        border_style="blue",
    ))

    console.print("\n[bold]Escenarios disponibles:[/bold]")
    for i, s in enumerate(SCENARIOS, 1):
        console.print(f"  {i:2}. [cyan]{s['name']}[/cyan]  [dim]({s['mode']})[/dim]")

    console.print()

    # URL del servidor
    url = console.input("[yellow]URL del servidor[/yellow] [dim](Enter = http://localhost:8000)[/dim]: ").strip()
    if not url:
        url = DEFAULT_URL

    # Número de tablets
    n_str = console.input("[yellow]¿Cuántas tablets simular?[/yellow] [dim](1-10, Enter = 5)[/dim]: ").strip()
    try:
        n = max(1, min(10, int(n_str)))
    except ValueError:
        n = 5

    # Intervalo
    i_str = console.input("[yellow]Intervalo entre heartbeats (segundos)[/yellow] [dim](Enter = 5)[/dim]: ").strip()
    try:
        interval = max(2, int(i_str))
    except ValueError:
        interval = 5

    # Contraseña admin
    pwd = console.input("[yellow]Contraseña admin del backend[/yellow] [dim](Enter = admin123)[/dim]: ").strip()
    if not pwd:
        pwd = "admin123"

    return url, n, interval, pwd


# ──────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TabletMonitor Simulator")
    parser.add_argument("--url",      default=None,      help="URL del servidor backend")
    parser.add_argument("--tablets",  type=int, default=None, help="Número de tablets (1-10)")
    parser.add_argument("--interval", type=int, default=None, help="Intervalo en segundos")
    parser.add_argument("--password", default=None,      help="Contraseña admin")
    args = parser.parse_args()

    if args.url and args.tablets and args.interval and args.password:
        # Modo no-interactivo (CI/testing)
        url, n, interval, pwd = args.url, args.tablets, args.interval, args.password
    else:
        url, n, interval, pwd = interactive_menu()

    try:
        asyncio.run(run_simulator(url, n, interval, pwd))
    except KeyboardInterrupt:
        console.print("\n[yellow]Simulador detenido.[/yellow]")