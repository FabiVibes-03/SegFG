import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { MapContainer, TileLayer, Marker, Popup, Circle } from 'react-leaflet'
import L from 'leaflet'
import { getDevices, getSummary, getAlerts } from '../api'
import { useWebSocket } from '../useWebSocket'
import { StatusBadge, StatBar } from '../components/Components'

// ── Íconos del mapa por estado ────────────────────────
const makeIcon = (color) => L.divIcon({
    className: '',
    html: `<div style="
    width:14px; height:14px; border-radius:50%;
    background:${color}; border:2px solid #0a0c0f;
    box-shadow: 0 0 8px ${color}88;
  "></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
})
const ICONS = {
    online: makeIcon('#3fb950'),
    warning: makeIcon('#d29922'),
    offline: makeIcon('#f85149'),
    lost: makeIcon('#e3632a'),
}

// ── Helpers ───────────────────────────────────────────
function timeAgo(ts) {
    if (!ts) return '—'
    const secs = Math.floor((Date.now() - new Date(ts + 'Z')) / 1000)
    if (secs < 60) return `hace ${secs}s`
    if (secs < 3600) return `hace ${Math.floor(secs / 60)}m`
    return `hace ${Math.floor(secs / 3600)}h`
}

export default function Dashboard() {
    const [devices, setDevices] = useState([])
    const [summary, setSummary] = useState(null)
    const [alerts, setAlerts] = useState([])
    const [filter, setFilter] = useState('all')
    const [search, setSearch] = useState('')
    const [loading, setLoading] = useState(true)

    const refresh = useCallback(async () => {
        try {
            const [devs, summ, alts] = await Promise.all([
                getDevices(),
                getSummary(),
                getAlerts(true),   // solo no leídas
            ])
            setDevices(devs)
            setSummary(summ)
            setAlerts(alts)
        } catch (err) {
            console.error('Error cargando datos:', err)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { refresh() }, [refresh])

    // WebSocket — refrescar cuando el servidor avisa cambios
    useWebSocket((event) => {
        if (event === 'devices_updated') refresh()
    })

    // Filtrado
    const filtered = devices.filter(d => {
        const matchFilter = filter === 'all' || d.status === filter
        const matchSearch = !search ||
            d.hostname.toLowerCase().includes(search.toLowerCase()) ||
            (d.display_name || '').toLowerCase().includes(search.toLowerCase()) ||
            (d.mac_address || '').toLowerCase().includes(search.toLowerCase())
        return matchFilter && matchSearch
    })

    // Tablets con GPS para el mapa
    const withLocation = devices.filter(d => d.last_lat && d.last_lng)

    if (loading) return <LoadingScreen />

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
            {/* ── Top bar ── */}
            <TopBar summary={summary} alerts={alerts} />

            <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
                {/* ── Sidebar ── */}
                <Sidebar summary={summary} filter={filter} setFilter={setFilter} alerts={alerts} />

                {/* ── Main content ── */}
                <main style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>

                    {/* Mapa */}
                    <div style={{ height: '280px', flexShrink: 0 }}>
                        <MapContainer
                            center={[20.97, -89.62]}
                            zoom={5}
                            style={{ height: '100%', width: '100%' }}
                            zoomControl={false}
                        >
                            <TileLayer
                                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                                attribution=""
                            />
                            {devices.map(d => d.last_lat && d.last_lng ? (
                                <Marker key={d.id} position={[d.last_lat, d.last_lng]} icon={ICONS[d.status] || ICONS.offline}>
                                    <Popup>
                                        <div style={{ fontFamily: 'var(--font-sans)', minWidth: '120px' }}>
                                            <strong>{d.display_name || d.hostname}</strong><br />
                                            <StatusBadge status={d.status} size="sm" />
                                        </div>
                                    </Popup>
                                </Marker>
                            ) : null)}
                        </MapContainer>
                    </div>

                    {/* Barra de búsqueda y filtro */}
                    <div style={{ padding: '16px 20px 8px', display: 'flex', gap: '10px', borderBottom: '1px solid var(--border)' }}>
                        <input
                            placeholder="Buscar por nombre, MAC..."
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            style={{ maxWidth: '300px' }}
                        />
                        <button className="btn-ghost" onClick={refresh} title="Refrescar">↺ Actualizar</button>
                    </div>

                    {/* Tabla de dispositivos */}
                    <div style={{ flex: 1, overflow: 'auto', padding: '0 20px 20px' }}>
                        <DeviceTable devices={filtered} />
                    </div>
                </main>
            </div>
        </div>
    )
}

// ── Top Bar ───────────────────────────────────────────

function TopBar({ summary, alerts }) {
    return (
        <header style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 20px',
            height: '52px',
            background: 'var(--bg-panel)',
            borderBottom: '1px solid var(--border)',
            flexShrink: 0,
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--blue)', letterSpacing: '0.1em' }}>
                    TABLETMONITOR
                </span>
                <span style={{ color: 'var(--border-accent)' }}>|</span>
                <span style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
                    {summary?.total_devices ?? 0} dispositivos
                </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                {alerts?.length > 0 && (
                    <Link to="/alerts" style={{
                        display: 'flex', alignItems: 'center', gap: '6px',
                        padding: '4px 10px', borderRadius: '4px',
                        background: 'var(--red-dim)', color: 'var(--red)',
                        fontFamily: 'var(--font-mono)', fontSize: '11px',
                        textDecoration: 'none',
                    }}>
                        <span className="pulse">⚠</span> {alerts.length} alerta{alerts.length > 1 ? 's' : ''}
                    </Link>
                )}
                <Link to="/alerts" className="btn-ghost" style={{ fontSize: '12px' }}>Alertas</Link>
            </div>
        </header>
    )
}

// ── Sidebar ───────────────────────────────────────────

function Sidebar({ summary, filter, setFilter, alerts }) {
    const FILTERS = [
        { id: 'all', label: 'Todos', count: summary?.total_devices },
        { id: 'online', label: 'En línea', count: summary?.online, color: 'var(--green)' },
        { id: 'warning', label: 'Alerta', count: summary?.warning, color: 'var(--yellow)' },
        { id: 'offline', label: 'Offline', count: summary?.offline, color: 'var(--red)' },
        { id: 'lost', label: 'Perdidas', count: summary?.lost, color: 'var(--orange)' },
    ]

    return (
        <aside style={{
            width: '200px',
            flexShrink: 0,
            background: 'var(--bg-panel)',
            borderRight: '1px solid var(--border)',
            padding: '16px 12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
            overflow: 'auto',
        }}>
            <div style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', letterSpacing: '0.1em', padding: '0 8px', marginBottom: '4px' }}>
                FILTRAR
            </div>
            {FILTERS.map(f => (
                <button
                    key={f.id}
                    onClick={() => setFilter(f.id)}
                    style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: '7px 10px',
                        borderRadius: 'var(--radius)',
                        background: filter === f.id ? 'var(--bg-hover)' : 'transparent',
                        border: filter === f.id ? '1px solid var(--border-accent)' : '1px solid transparent',
                        color: f.color || 'var(--text-primary)',
                        cursor: 'pointer',
                        fontSize: '13px',
                        textAlign: 'left',
                    }}
                >
                    <span>{f.label}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)' }}>
                        {f.count ?? 0}
                    </span>
                </button>
            ))}

            <div style={{ borderTop: '1px solid var(--border)', margin: '12px 0 8px' }} />
            <div style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', letterSpacing: '0.1em', padding: '0 8px', marginBottom: '4px' }}>
                NAVEGACIÓN
            </div>
            <Link to="/alerts" style={{
                padding: '7px 10px', borderRadius: 'var(--radius)', color: 'var(--text-secondary)',
                fontSize: '13px', display: 'flex', justifyContent: 'space-between',
            }}>
                Alertas
                {(summary?.unread_alerts ?? 0) > 0 && (
                    <span style={{ background: 'var(--red)', color: '#fff', borderRadius: '10px', padding: '0 6px', fontSize: '10px', fontFamily: 'var(--font-mono)' }}>
                        {summary.unread_alerts}
                    </span>
                )}
            </Link>
        </aside>
    )
}

// ── Device Table ──────────────────────────────────────

function DeviceTable({ devices }) {
    if (devices.length === 0) {
        return (
            <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                SIN DISPOSITIVOS
            </div>
        )
    }

    const TH = ({ children, style }) => (
        <th style={{
            padding: '10px 16px',
            textAlign: 'left',
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            color: 'var(--text-muted)',
            fontWeight: 400,
            letterSpacing: '0.08em',
            whiteSpace: 'nowrap',
            borderBottom: '1px solid var(--border)',
            ...style,
        }}>{children}</th>
    )

    return (
        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '8px' }}>
            <thead>
                <tr>
                    <TH>DISPOSITIVO</TH>
                    <TH>ESTADO</TH>
                    <TH>BATERÍA</TH>
                    <TH>RED / SSID</TH>
                    <TH>CPU</TH>
                    <TH>ÚLTIMO REPORTE</TH>
                    <TH></TH>
                </tr>
            </thead>
            <tbody>
                {devices.map(d => <DeviceRow key={d.id} device={d} />)}
            </tbody>
        </table>
    )
}

function DeviceRow({ device: d }) {
    return (
        <tr style={{ borderBottom: '1px solid var(--border)', transition: 'background var(--transition)' }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-hover)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
        >
            {/* Nombre */}
            <td style={{ padding: '12px 16px' }}>
                <div style={{ fontWeight: 500 }}>{d.display_name || d.hostname}</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)' }}>
                    {d.mac_address}
                </div>
            </td>

            {/* Estado */}
            <td style={{ padding: '12px 16px' }}>
                <StatusBadge status={d.status} size="sm" />
            </td>

            {/* Batería */}
            <td style={{ padding: '12px 16px', minWidth: '100px' }}>
                {d.last_battery != null ? (
                    <StatBar label="" value={d.last_battery} warn={20} crit={10} />
                ) : (
                    <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>N/A</span>
                )}
            </td>

            {/* SSID */}
            <td style={{ padding: '12px 16px' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)' }}>
                    {d.last_ssid || '—'}
                </span>
            </td>

            {/* CPU */}
            <td style={{ padding: '12px 16px' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)' }}>
                    {d.last_cpu != null ? `${Math.round(d.last_cpu)}%` : '—'}
                </span>
            </td>

            {/* Último reporte */}
            <td style={{ padding: '12px 16px' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)' }}>
                    {timeAgo(d.last_seen)}
                </span>
            </td>

            {/* Detalle */}
            <td style={{ padding: '12px 16px' }}>
                <Link to={`/device/${d.id}`} className="btn-ghost" style={{ fontSize: '11px', padding: '4px 10px' }}>
                    Ver →
                </Link>
            </td>
        </tr>
    )
}

function LoadingScreen() {
    return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', flexDirection: 'column', gap: '12px' }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-muted)', letterSpacing: '0.2em' }}>
                CARGANDO...
            </div>
        </div>
    )
}