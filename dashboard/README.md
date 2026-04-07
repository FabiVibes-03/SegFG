# TabletMonitor — Dashboard

## Requisitos
- Node.js 18+

## Instalación y desarrollo

```bash
cd dashboard
npm install
npm run dev
# Abre http://localhost:3000
```

## Build para producción

```bash
npm run build
# Genera dist/ — sirve con cualquier servidor estático (nginx, Apache, etc.)
```

## Configuración

En desarrollo el proxy de Vite redirige `/api` y `/ws` a `http://localhost:8000`.

En producción crea un archivo `.env.production`:
```
VITE_API_URL=http://TU_SERVIDOR:8000
VITE_WS_URL=ws://TU_SERVIDOR:8000/ws
```

## Páginas

| Ruta | Descripción |
|------|-------------|
| `/login` | Acceso con contraseña de admin |
| `/` | Dashboard principal — mapa + tabla de dispositivos |
| `/device/:id` | Detalle: stats, gráficas históricas, comandos remotos |
| `/alerts` | Listado de alertas con reconocimiento |