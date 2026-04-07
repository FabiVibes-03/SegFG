import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { getAlerts, acknowledgeAlert, acknowledgeAll } from '../api'

const ALERT_CONFIG = {
    offline: { icon: '📡', color: 'var(--red)', label: 'Sin conexión' },
    unknown_network: { icon: '⚠️', color: 'var(--yellow)', label: 'Red desconocida' },
    geofence: { icon: '📍', color: 'var(--orange)', label: 'Fuera de zona' },
    low_battery: { icon: '🪫', color: 'var(--yellow)', label: 'Batería baja' },
    back_online: { icon: '✅', color: 'var(--green)', label: 'Volvió en línea' },
}

function timeStr(ts) {
    return new Date(ts + 'Z').toLocaleString('es-MX', { dateStyle: 'short', timeStyle: 'short' })
}

export default function Alerts() {
    const [alerts, setAlerts] = useState([])
    const [loading, setLoading] = useState(true)
    const [filter, setFilter] = useState('unread')

    const load = useCallback(async () => {
        setLoading(true)
        try {
            const data = await getAlerts(false)  // todas
            setAlerts(data)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { load() }, [load])

    const ackOne = async (id) => {
        await acknowledgeAlert(id)
        setAlerts(prev => prev.map(a => a.id === id ? { ...a, acknowledged: true } : a))
    }

    const ackAll = async () => {
        await acknowledgeAll()
        setAlerts(prev => prev.map(a => ({ ...a, acknowledged: true })))
    }

    const visible = alerts.filter(a => filter === 'all' ? true : !a.acknowledged)
    const unreadCount = alerts.filter(a => !a.acknowledged).length

    return (
        <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
            {/* Header */}
            <div style={{ background: 'var(--bg-panel)', borderBottom: '1px solid var(--border)', padding: '16px 24px', display: 'flex', alignItems: 'center', gap: '16px' }}>
                <Link to="/" style={{ color: 'var(--text-muted)', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>← VOLVER</Link>
                <span style={{ color: 'var(--border-accent)' }}>|</span>
                <h1 style={{ fontSize: '18px', fontWeight: 600 }}>Alertas</h1>
                {unreadCount > 0 && (
                    <span style={{ background: 'var(--red)', color: '#fff', borderRadius: '10px', padding: '2px 8px', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                        {unreadCount}
                    </span>
                )}

                <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px' }}>
                    {/* Filtro */}
                    <div style={{ display: 'flex', border: '1px solid var(--border)', borderRadius: 'var(--radius)', overflow: 'hidden' }}>
                        {['unread', 'all'].map(f => (
                            <button
                                key={f}
                                onClick={() => setFilter(f)}
                                style={{
                                    background: filter === f ? 'var(--bg-hover)' : 'transparent',
                                    color: filter === f ? 'var(--text-primary)' : 'var(--text-muted)',
                                    borderRadius: 0, border: 'none', padding: '6px 14px', fontSize: '12px',
                                    borderRight: f === 'unread' ? '1px solid var(--border)' : 'none',
                                }}
                            >
                                {f === 'unread' ? `Sin leer (${unreadCount})` : `Todas (${alerts.length})`}
                            </button>
                        ))}
                    </div>

                    {unreadCount > 0 && (
                        <button className="btn-ghost" onClick={ackAll} style={{ fontSize: '12px' }}>
                            ✓ Marcar todo como leído
                        </button>
                    )}

                    <button className="btn-ghost" onClick={load} style={{ fontSize: '12px' }}>
                        ↺
                    </button>
                </div>
            </div>

            <div style={{ padding: '24px', maxWidth: '900px' }}>
                {loading ? (
                    <div style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>CARGANDO...</div>
                ) : visible.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                        {filter === 'unread' ? 'SIN ALERTAS PENDIENTES ✓' : 'SIN ALERTAS REGISTRADAS'}
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {visible.map(alert => {
                            const cfg = ALERT_CONFIG[alert.type] || { icon: '●', color: 'var(--text-muted)', label: alert.type }
                            return (
                                <div
                                    key={alert.id}
                                    className="card fade-in"
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '14px',
                                        opacity: alert.acknowledged ? 0.45 : 1,
                                        padding: '14px 16px',
                                        borderLeft: `3px solid ${alert.acknowledged ? 'var(--border)' : cfg.color}`,
                                    }}
                                >
                                    <span style={{ fontSize: '18px', flexShrink: 0 }}>{cfg.icon}</span>

                                    <div style={{ flex: 1, minWidth: 0 }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '3px' }}>
                                            <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: cfg.color, letterSpacing: '0.05em' }}>
                                                {cfg.label.toUpperCase()}
                                            </span>
                                            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                                                {timeStr(alert.created_at)}
                                            </span>
                                        </div>
                                        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                            {alert.message}
                                        </p>
                                    </div>

                                    <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
                                        <Link
                                            to={`/device/${alert.device_id}`}
                                            className="btn-ghost"
                                            style={{ fontSize: '11px', padding: '4px 10px' }}
                                        >
                                            Ver dispositivo
                                        </Link>
                                        {!alert.acknowledged && (
                                            <button
                                                className="btn-ghost"
                                                onClick={() => ackOne(alert.id)}
                                                style={{ fontSize: '11px', padding: '4px 10px', color: 'var(--green)' }}
                                            >
                                                ✓ Leído
                                            </button>
                                        )}
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                )}
            </div>
        </div>
    )
}