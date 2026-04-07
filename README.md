# 🖥️ SegFG

> Sistema de monitoreo y seguridad en tiempo real para flotas de dispositivos Windows en red.

![Estado](https://img.shields.io/badge/estado-estable-green)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![.NET](https://img.shields.io/badge/.NET-8.0-purple)
![React](https://img.shields.io/badge/React-18-61dafb)

---

## ¿Qué es SegFG?

SegFG es una solución completa de monitoreo y seguridad para flotas de tablets o computadoras Windows. Permite a los administradores visualizar en tiempo real el estado de cada dispositivo, recibir alertas automáticas ante situaciones de riesgo y ejecutar acciones remotas como bloqueo de pantalla o apagado.

Diseñado para entornos donde se necesita mantener control sobre dispositivos compartidos o de campo, como escuelas, bodegas, clínicas, puntos de venta o cualquier organización con múltiples equipos Windows en red.

---

## ✨ Funcionalidades

| Función | Descripción |
|---|---|
| 📡 Monitoreo en tiempo real | Estado de cada tablet actualizado cada 30 segundos |
| 🔋 Telemetría completa | Batería, CPU, RAM, disco, red WiFi y GPS (si disponible) |
| 🗺️ Mapa de ubicaciones | Visualización de todos los dispositivos en mapa interactivo |
| ⚠️ Alertas automáticas | Red desconocida, batería baja, fuera de zona, sin conexión |
| 📍 Geofencing | Define zonas autorizadas y recibe alerta si un equipo las abandona |
| 🔒 Comandos remotos | Bloquear pantalla, apagar, activar alarma sonora, enviar mensaje |
| 📊 Historial | Gráficas de batería y CPU de los últimos 60 reportes |
| 🛡️ Seguridad | Tokens únicos por dispositivo, JWT para el admin, servicio protegido en Windows |

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                     TABLETS (x10)                           │
│           Windows Service "TabletMonitor"                   │
│      Recopila telemetría y envía cada 30s via HTTPS         │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  SERVIDOR CENTRAL                           │
│     FastAPI + PostgreSQL + WebSocket + APScheduler         │
└────────────────────────┬────────────────────────────────────┘
                         │ WebSocket (tiempo real)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               DASHBOARD WEB                                 │
│         React + Leaflet — mapa, tabla, alertas             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Estructura del proyecto

```
TabletMonitor/
├── backend/                ← Servidor API (Python / FastAPI)
│   ├── main.py             ← Entrada de la app + WebSocket
│   ├── run.py              ← Script de arranque recomendado
│   ├── config.py           ← Configuración desde .env
│   ├── database.py         ← Conexión async a PostgreSQL
│   ├── models.py           ← Tablas de la base de datos
│   ├── schemas.py          ← Validación de datos (Pydantic)
│   ├── auth.py             ← Tokens por dispositivo + JWT admin
│   ├── simulator.py        ← Simulador de tablets para pruebas
│   ├── .env                ← Variables de entorno (NO subir a Git)
│   ├── .env.example        ← Plantilla del .env
│   ├── requirements.txt
│   ├── routers/
│   │   ├── devices.py      ← Registro y gestión de tablets
│   │   ├── heartbeat.py    ← Recepción de telemetría
│   │   └── commands.py     ← Comandos remotos y alertas
│   └── services/
│       └── alert_service.py ← Lógica de detección de alertas
│
├── agent/                  ← Agente Windows (C# / .NET 8)
│   ├── TabletMonitor.csproj
│   ├── Program.cs          ← Entrada + instalación como servicio
│   ├── Worker.cs           ← Loop principal cada 30s
│   ├── appsettings.json    ← URL del servidor y configuración
│   ├── Models/
│   │   └── Models.cs       ← Payload, respuesta, comandos
│   └── Services/
│       ├── TelemetryService.cs   ← WMI: batería, CPU, WiFi, GPS
│       ├── ApiService.cs         ← Comunicación HTTPS con backend
│       ├── RegistrationService.cs ← Registro inicial + token
│       ├── CommandExecutor.cs    ← Ejecuta lock, shutdown, alarm
│       └── ServiceInstaller.cs  ← Instala/desinstala el servicio
│
└── dashboard/              ← Panel de control (React / Vite)
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── App.jsx          ← Rutas y guard de autenticación
        ├── api.js           ← Llamadas al backend
        ├── useWebSocket.js  ← Tiempo real con reconexión automática
        ├── index.css        ← Design system
        ├── components/
        │   └── Components.jsx  ← StatusBadge, StatBar, CommandPanel
        └── pages/
            ├── Login.jsx
            ├── Dashboard.jsx    ← Mapa + tabla principal
            ├── DeviceDetail.jsx ← Stats, historial, comandos
            └── Alerts.jsx       ← Alertas con reconocimiento
```

---

## 🔄 Flujo de trabajo

### Registro inicial de una tablet
```
Tablet                          Servidor
  │                                │
  │── POST /api/register ─────────►│
  │   { hostname, mac_address }    │── genera token único SHA-256
  │                                │── guarda en PostgreSQL
  │◄── { device_id, api_token } ───│
  │                                │
  │  Guarda token en registro      │
  │  de Windows (HKLM)             │
```

### Ciclo de heartbeat (cada 30 segundos)
```
Tablet                          Servidor
  │  Recopila: IP, SSID, batería,  │
  │  CPU, RAM, GPS, usuario...     │
  │                                │
  │── POST /api/heartbeat ────────►│── valida token
  │   Authorization: Bearer token  │── guarda heartbeat en DB
  │                                │── evalúa alertas
  │◄── { status, commands[] } ─────│
  │                                │
  │  Ejecuta comandos si hay:      │
  │  lock / alarm / message        │
```

### Detección automática de alertas
```
Servidor evalúa cada heartbeat:

  ¿SSID está en lista blanca?  ──No──► ALERTA: red desconocida
           │ Sí
  ¿GPS fuera del geofence?     ──Sí──► ALERTA: fuera de zona
           │ No
  ¿Batería < 10%?              ──Sí──► ALERTA: batería crítica
           │ No
  Todo OK ──────────────────────────► estado: online

Worker cada 60s:
  Sin heartbeat > 2 min  ──► WARNING
  Sin heartbeat > 5 min  ──► OFFLINE + alerta
  Sin heartbeat > 10 min ──► LOST   + alerta crítica
```

---

## 🚀 Instalación y configuración

### Requisitos previos
- Python 3.11+
- Node.js 18+
- .NET 8 SDK (para compilar el agente)
- PostgreSQL 14+

---

### 1. Backend

```bash
cd backend

# Crear entorno virtual
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
copy .env.example .env
# Editar .env con tus valores (ver sección Configuración)

# Crear base de datos en PostgreSQL
# Abrir psql como superusuario y ejecutar:
# CREATE USER monitor WITH PASSWORD 'monitor123';
# CREATE DATABASE tabletmonitor OWNER monitor;

# Arrancar el servidor
python run.py
# API disponible en http://localhost:8000
# Documentación interactiva en http://localhost:8000/docs
```

---

### 2. Dashboard

```bash
cd dashboard

npm install
npm run dev
# Dashboard disponible en http://localhost:3000
```

Para producción:
```bash
npm run build
# Sirve la carpeta dist/ con nginx o cualquier servidor estático
```

---

### 3. Agente (en cada tablet)

```bash
# Compilar (en la máquina de desarrollo)
cd agent
dotnet publish -c Release -r win-x64 --self-contained true \
  -p:PublishSingleFile=true -o ./publish

# Editar appsettings.json antes de distribuir:
# "Url": "http://IP_DEL_SERVIDOR:8000"

# En cada tablet — ejecutar como Administrador
TabletMonitor.exe install
```

El agente se instala como Windows Service con inicio automático y se registra solo en el servidor la primera vez.

---

### 4. Simulador de pruebas

```bash
cd backend
pip install httpx rich
python simulator.py
```

Simula hasta 10 tablets con distintos escenarios: batería baja, red desconocida, GPS fuera de zona, desconexión, CPU alta, etc.

---

## ⚙️ Configuración

### Backend — archivo `.env`

| Variable | Descripción | Default |
|---|---|---|
| `DATABASE_URL` | Cadena de conexión a PostgreSQL | `postgresql+asyncpg://monitor:monitor123@localhost:5432/tabletmonitor` |
| `SECRET_KEY` | Clave para firmar JWT — generar con `python -c "import secrets; print(secrets.token_hex(32))"` | — |
| `ADMIN_PASSWORD` | Contraseña del dashboard | `admin123` |
| `WARN_AFTER_SECONDS` | Segundos sin heartbeat para pasar a WARNING | `120` |
| `OFFLINE_AFTER_SECONDS` | Segundos para pasar a OFFLINE | `300` |
| `LOST_AFTER_SECONDS` | Segundos para pasar a LOST | `600` |

### Agente — `appsettings.json`

| Campo | Descripción |
|---|---|
| `Server.Url` | URL del servidor backend (ej: `http://192.168.1.100:8000`) |
| `Agent.HeartbeatIntervalSeconds` | Cada cuántos segundos enviar telemetría (default: `30`) |

---

## 🔐 Seguridad

- Cada tablet tiene un **token único SHA-256** generado al registrarse, guardado en el registro de Windows (`HKLM\SOFTWARE\TabletMonitor`) — solo accesible por SYSTEM y administradores.
- El dashboard usa **JWT con expiración de 12 horas**.
- El Windows Service está configurado para que **usuarios normales no puedan detenerlo**.
- El servicio se **recupera automáticamente** si falla (reintentos a los 10s, 30s, 60s).
- Toda la comunicación entre agente y servidor se realiza via **HTTPS** (en producción con certificado SSL).

---

## 📡 API — Endpoints principales

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `POST` | `/api/admin/login` | Login del dashboard | — |
| `POST` | `/api/register` | Registro de tablet | — |
| `POST` | `/api/heartbeat` | Telemetría del agente | Bearer token dispositivo |
| `GET` | `/api/devices` | Lista de tablets | JWT admin |
| `GET` | `/api/devices/:id` | Detalle de tablet | JWT admin |
| `GET` | `/api/devices/:id/history` | Historial de heartbeats | JWT admin |
| `GET` | `/api/summary` | Resumen del dashboard | JWT admin |
| `POST` | `/api/devices/:id/command` | Enviar comando remoto | JWT admin |
| `GET` | `/api/alerts` | Lista de alertas | JWT admin |
| `PATCH` | `/api/alerts/:id/acknowledge` | Marcar alerta como leída | JWT admin |
| `GET` | `/api/networks` | Redes WiFi autorizadas | JWT admin |
| `POST` | `/api/networks` | Agregar red autorizada | JWT admin |
| `POST` | `/api/geofences` | Crear zona geográfica | JWT admin |
| `WS` | `/ws` | WebSocket tiempo real | — |

Documentación interactiva completa disponible en `/docs` (Swagger UI).

---

## 🗃️ Base de datos

| Tabla | Descripción |
|---|---|
| `devices` | Dispositivos registrados y su estado actual |
| `heartbeats` | Historial completo de telemetría |
| `alerts` | Alertas generadas automáticamente |
| `commands` | Cola de comandos remotos pendientes |
| `allowed_networks` | Redes WiFi autorizadas |
| `geofences` | Zonas geográficas autorizadas |

---

## 🛠️ Stack tecnológico

| Componente | Tecnología |
|---|---|
| Agente | C# / .NET 8 Worker Service |
| Backend | Python 3.11 / FastAPI / SQLAlchemy async |
| Base de datos | PostgreSQL 16 |
| Dashboard | React 18 / Vite / Leaflet / Recharts |
| Tiempo real | WebSocket nativo |
| Auth | SHA-256 (dispositivos) + JWT (admin) |
| Scheduler | APScheduler |

---

## 📋 Comandos remotos disponibles

| Comando | Efecto en la tablet |
|---|---|
| `lock` | Bloquea la pantalla inmediatamente |
| `shutdown` | Apaga el equipo en 30 segundos |
| `alarm` | Activa alarma sonora por 30 segundos |
| `message` | Muestra un mensaje popup en pantalla |

Los comandos se encolan en el servidor y se ejecutan en el próximo heartbeat del agente (latencia máxima de 30 segundos).

---

## 🤝 Contribución

1. Haz fork del repositorio
2. Crea una rama: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -m "Agrega nueva funcionalidad"`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Abre un Pull Request

---

## 📄 Licencia

MIT License — libre para uso personal y comercial.
