# TabletMonitor — Backend

## Requisitos
- Python 3.11+
- PostgreSQL 14+ (o usar SQLite para desarrollo)

## Instalación rápida

```bash
# 1. Entrar a la carpeta
cd backend

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar entorno
copy .env.example .env
# Editar .env con tus valores

# 5. Crear base de datos en PostgreSQL
# Opción A — psql
psql -U postgres -c "CREATE USER monitor WITH PASSWORD 'monitor123';"
psql -U postgres -c "CREATE DATABASE tabletmonitor OWNER monitor;"

# 6. Iniciar el servidor
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Documentación interactiva
Abre http://localhost:8000/docs para ver todos los endpoints con Swagger UI.

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | /api/admin/login | Login del dashboard |
| POST | /api/register | Registro de tablet (agente) |
| POST | /api/heartbeat | Telemetría (agente) |
| GET  | /api/devices | Lista de tablets |
| GET  | /api/summary | Resumen del dashboard |
| GET  | /api/alerts | Alertas generadas |
| POST | /api/devices/{id}/command | Enviar comando remoto |
| GET  | /api/networks | Redes WiFi autorizadas |
| WS   | /ws | WebSocket tiempo real |

## Para producción (VPS)

```bash
# Instalar con gunicorn
pip install gunicorn

# Correr con múltiples workers
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# O usar systemd / supervisor para que corra como servicio
```