import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { getDevice, getHistory, updateDevice } from '../api'
import { StatusBadge, StatBar, CommandPanel } from '../components/Components'

function timeLabel(ts) {
    const d = new Date(ts + 'Z')
    return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

export default function DeviceDetail() {
    const { id } = useParams()
    const [device, setDevice] = useState(null)
    const [history, setHistory] = useState([])
    const [editing, setEditing] = useState(false)
    const [name, setName] = useState('')
    const [notes, setNotes] = useState('')
    const [loading, setLoading] = useState(true)

    const load = useCallback(async () => {
        try {
            const [dev, hist] = await Promise.all([getDevice(id), getHistory(id, 60)])
            setDevice(dev)
            setHistory(hist.reverse()) // cronológico para la gráfica
            setName(dev.display_name || dev.hostname)
            setNotes(dev.notes || '')
        } catch (err) {
            console.error(err)
        } finally {
            setLoading(false)
        }
    }, [id])

    useEffect(() => { load() }, [load])

    const saveEdit = async () => {
        await updateDevice(id, { display_name: name, notes })
        setEditing(false)
        load()
    }

    if (loading) return <div style={{ padding: '40px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>CARGANDO...</div>
    if (!device) return <div style={{ padding: '40px', color: 'var(--red)' }}>Dispositivo no encontrado</div>

    const last = history[history.length - 1]

    return (
        <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
            {/* Header */}
            <div style={{ background: 'var(--bg-panel)', borderBottom: '1px solid var(--border)', padding: '16px 24px', display: 'flex', alignItems: 'center', gap: '16px' }}>
                <Link to="/" style={{ color: 'var(--text-muted)', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>← VOLVER</Link>
                <span style={{ color: 'var(--border-accent)' }}>|</span>

                {!editing ? (
                    <>
                        <h1 style={{ fontSize: '18px', fontWeight: 600 }}>{device.display_name || device.hostname}</h1>
                        <StatusBadge status={device.status} />
                        <button className="btn-ghost" onClick={() => setEditing(true)} style={{ marginLeft: 'auto', fontSize: '12px' }}>
                            ✏ Editar
                        </button>
                    </>
                ) : (
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flex: 1 }}>
                        <input value={name} onChange={e => setName(e.target.value)} style={{ maxWidth: '240px' }} />
                        <button className="btn-primary" onClick={saveEdit}>Guardar</button>
                        <button className="btn-ghost" onClick={() => setEditing(false)}>Cancelar</button>
                    </div>
                )}
            </div>

            <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '1100px' }}>

                {/* Info + stats actuales */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
                    {/* Info */}
                    <div className="card">
                        <SectionTitle>Información</SectionTitle>
                        <InfoRow label="Hostname" value={device.hostname} />
                        <InfoRow label="MAC" value={device.mac_address} mono />
                        <InfoRow label="IP" value={last?.ip_address || '—'} mono />
                        <InfoRow label="OS" value={last?.os_version || '—'} />
                        <InfoRow label="Usuario" value={last?.active_user || '—'} />
                        <InfoRow label="Uptime" value={last?.uptime_seconds ? formatUptime(last.uptime_seconds) : '—'} />
                        <InfoRow label="Registrado" value={new Date(device.registered_at).toLocaleDateString('es-MX')} />
                    </div>

                    {/* Red */}
                    <div className="card">
                        <SectionTitle>Red</SectionTitle>
                        <InfoRow label="SSID" value={last?.ssid || '—'} />
                        <InfoRow label="IP" value={last?.ip_address || '—'} mono />
                        <div style={{ marginTop: '16px' }}>
                            <SectionTitle>Pantalla</SectionTitle>
                            <InfoRow label="Bloqueada" value={last?.screen_locked ? '🔒 Sí' : '🔓 No'} />
                        </div>
                        {last?.latitude && (
                            <div style={{ marginTop: '16px' }}>
                                <SectionTitle>GPS</SectionTitle>
                                <InfoRow label="Lat" value={last.latitude.toFixed(5)} mono />
                                <InfoRow label="Lng" value={last.longitude.toFixed(5)} mono />
                            </div>
                        )}
                    </div>

                    {/* Hardware actual */}
                    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                        <SectionTitle>Hardware actual</SectionTitle>
                        <StatBar label="BATERÍA" value={last?.battery_level} warn={20} crit={10} />
                        <StatBar label="CPU" value={last?.cpu_usage} warn={80} crit={95} />
                        {last?.ram_used_mb && last?.ram_total_mb && (
                            <StatBar label="RAM" value={last.ram_used_mb} max={last.ram_total_mb} unit=" MB" warn={80} crit={90} />
                        )}
                        {last?.disk_free_gb != null && last?.disk_total_gb && (
                            <StatBar
                                label="DISCO LIBRE"
                                value={last.disk_free_gb}
                                max={last.disk_total_gb}
                                unit=" GB"
                                warn={20}
                                crit={10}
                            />
                        )}
                    </div>
                </div>

                {/* Gráficas históricas */}
                <div className="card">
                    <SectionTitle>Historial (últimos 60 reportes)</SectionTitle>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginTop: '16px' }}>
                        <MiniChart data={history} dataKey="battery_level" label="Batería (%)" color="var(--green)" domain={[0, 100]} />
                        <MiniChart data={history} dataKey="cpu_usage" label="CPU (%)" color="var(--blue)" domain={[0, 100]} />
                    </div>
                </div>

                {/* Notas */}
                <div className="card">
                    <SectionTitle>Notas</SectionTitle>
                    {!editing ? (
                        <p style={{ color: notes ? 'var(--text-secondary)' : 'var(--text-muted)', fontSize: '13px', marginTop: '8px' }}>
                            {notes || 'Sin notas. Haz click en "Editar" para agregar.'}
                        </p>
                    ) : (
                        <textarea
                            value={notes}
                            onChange={e => setNotes(e.target.value)}
                            rows={3}
                            style={{
                                width: '100%', marginTop: '8px', resize: 'vertical',
                                background: 'var(--bg-base)', color: 'var(--text-primary)',
                                border: '1px solid var(--border)', borderRadius: 'var(--radius)',
                                padding: '10px', fontFamily: 'var(--font-sans)', fontSize: '13px',
                            }}
                        />
                    )}
                </div>

                {/* Comandos remotos */}
                <div className="card">
                    <SectionTitle>Comandos remotos</SectionTitle>
                    <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '14px', fontFamily: 'var(--font-mono)' }}>
                        Los comandos se ejecutan en el próximo heartbeat del agente (≤ 30 segundos).
                    </p>
                    <CommandPanel deviceId={device.id} onDone={load} />
                </div>

            </div>
        </div>
    )
}

// ── Subcomponentes ────────────────────────────────────

function SectionTitle({ children }) {
    return (
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '10px' }}>
            {children}
        </div>
    )
}

function InfoRow({ label, value, mono }) {
    return (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '5px 0', borderBottom: '1px solid var(--border)' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{label}</span>
            <span style={{
                fontSize: '12px', color: 'var(--text-secondary)', maxWidth: '200px',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                fontFamily: mono ? 'var(--font-mono)' : 'var(--font-sans)',
            }}>{value || '—'}</span>
        </div>
    )
}

function MiniChart({ data, dataKey, label, color, domain }) {
    const chartData = data.map(h => ({
        t: timeLabel(h.timestamp),
        v: h[dataKey] != null ? Math.round(h[dataKey]) : null,
    })).filter(h => h.v != null)

    if (chartData.length === 0) return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '120px', color: 'var(--text-muted)', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>
            SIN DATOS
        </div>
    )

    return (
        <div>
            <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginBottom: '8px' }}>{label}</div>
            <ResponsiveContainer width="100%" height={120}>
                <LineChart data={chartData}>
                    <XAxis dataKey="t" tick={{ fontSize: 10, fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }} interval="preserveStartEnd" />
                    <YAxis domain={domain} tick={{ fontSize: 10, fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }} width={28} />
                    <Tooltip
                        contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', fontSize: '11px', fontFamily: 'var(--font-mono)' }}
                        labelStyle={{ color: 'var(--text-muted)' }}
                        itemStyle={{ color }}
                    />
                    <Line type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} dot={false} activeDot={{ r: 3 }} />
                </LineChart>
            </ResponsiveContainer>
        </div>
    )
}

function formatUptime(secs) {
    const h = Math.floor(secs / 3600)
    const m = Math.floor((secs % 3600) / 60)
    return h > 0 ? `${h}h ${m}m` : `${m}m`
}