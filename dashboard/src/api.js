// URL base — en dev usa el proxy de Vite, en prod cambia a tu servidor
const BASE = import.meta.env.VITE_API_URL || ''

let _token = localStorage.getItem('admin_token') || ''

export function setToken(t) {
    _token = t
    localStorage.setItem('admin_token', t)
}

export function clearToken() {
    _token = ''
    localStorage.removeItem('admin_token')
}

export function hasToken() {
    return !!_token
}

async function req(method, path, body) {
    const res = await fetch(`${BASE}${path}`, {
        method,
        headers: {
            'Content-Type': 'application/json',
            ..._token ? { Authorization: `Bearer ${_token}` } : {},
        },
        body: body ? JSON.stringify(body) : undefined,
    })
    if (res.status === 401) {
        clearToken()
        window.location.href = '/login'
        throw new Error('No autorizado')
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return res.json()
}

const get = (path) => req('GET', path)
const post = (path, body) => req('POST', path, body)
const patch = (path, body) => req('PATCH', path, body)
const del = (path) => req('DELETE', path)

// ── Auth ──────────────────────────────────────────────
export const login = (password) => post('/api/admin/login', { password })

// ── Devices ───────────────────────────────────────────
export const getDevices = () => get('/api/devices')
export const getDevice = (id) => get(`/api/devices/${id}`)
export const updateDevice = (id, body) => patch(`/api/devices/${id}`, body)
export const getHistory = (id, limit = 100) => get(`/api/devices/${id}/history?limit=${limit}`)
export const getSummary = () => get('/api/summary')

// ── Commands ──────────────────────────────────────────
export const sendCommand = (id, command, payload) =>
    post(`/api/devices/${id}/command`, { command, payload })

// ── Alerts ────────────────────────────────────────────
export const getAlerts = (onlyUnread = false) =>
    get(`/api/alerts?only_unread=${onlyUnread}&limit=200`)
export const acknowledgeAlert = (id) => patch(`/api/alerts/${id}/acknowledge`)
export const acknowledgeAll = () => patch('/api/alerts/acknowledge-all')

// ── Networks ──────────────────────────────────────────
export const getNetworks = () => get('/api/networks')
export const addNetwork = (ssid, desc) => post('/api/networks', { ssid, description: desc })
export const deleteNetwork = (id) => del(`/api/networks/${id}`)

// ── Geofences ─────────────────────────────────────────
export const getGeofences = () => get('/api/geofences')
export const createGeofence = (body) => post('/api/geofences', body)
export const deleteGeofence = (id) => del(`/api/geofences/${id}`)