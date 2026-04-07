import { useState } from 'react'
import { sendCommand } from '../api'

// ─────────────────────────────────────────────────────
// StatusBadge — muestra el estado del dispositivo
// ─────────────────────────────────────────────────────

const STATUS_CONFIG = {
    online: { label: 'EN LÍNEA', color: 'var(--green)', bg: 'var(--green-dim)', pulse: false },
    warning: { label: 'ALERTA', color: 'var(--yellow)', bg: 'var(--yellow-dim)', pulse: true },
    offline: { label: 'OFFLINE', color: 'var(--red)', bg: 'var(--red-dim)', pulse: false },
    lost: { label: 'PERDIDA', color: 'var(--orange)', bg: 'var(--orange-dim)', pulse: true },
}

export function StatusBadge({ status, size = 'md' }) {
    const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.offline
    const padding = size === 'sm' ? '2px 8px' : '4px 10px'
    const fontSize = size === 'sm' ? '10px' : '11px'

    return (
        <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '5px',
            padding,
            borderRadius: '4px',
            background: cfg.bg,
            color: cfg.color,
            fontFamily: 'var(--font-mono)',
            fontSize,
            fontWeight: 700,
            letterSpacing: '0.05em',
            border: `1px solid ${cfg.color}33`,
        }}>
            <span style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: cfg.color,
                flexShrink: 0,
                animation: cfg.pulse ? 'pulse 1.8s ease infinite' : 'none',
            }} />
            {cfg.label}
        </span>
    )
}

// ─────────────────────────────────────────────────────
// StatBar — barra de progreso para batería/CPU/RAM
// ─────────────────────────────────────────────────────

export function StatBar({ label, value, max = 100, unit = '%', warn = 30, crit = 15 }) {
    if (value == null) return null

    const pct = Math.min((value / max) * 100, 100)
    const color = pct <= crit ? 'var(--red)'
        : pct <= warn ? 'var(--yellow)'
            : 'var(--green)'

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--text-secondary)', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                    {label}
                </span>
                <span style={{ color: 'var(--text-primary)', fontSize: '11px', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                    {typeof value === 'number' && unit === '%' ? `${Math.round(value)}%` : `${value}${unit}`}
                </span>
            </div>
            <div style={{ height: '4px', background: 'var(--bg-base)', borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{
                    height: '100%',
                    width: `${pct}%`,
                    background: color,
                    borderRadius: '2px',
                    transition: 'width 600ms ease',
                }} />
            </div>
        </div>
    )
}

// ─────────────────────────────────────────────────────
// CommandPanel — botones de comandos remotos
// ─────────────────────────────────────────────────────

export function CommandPanel({ deviceId, onDone }) {
    const [loading, setLoading] = useState(null)
    const [message, setMessage] = useState('')
    const [showMsg, setShowMsg] = useState(false)
    const [feedback, setFeedback] = useState(null)

    const send = async (command, payload) => {
        setLoading(command)
        setFeedback(null)
        try {
            await sendCommand(deviceId, command, payload)
            setFeedback({ ok: true, text: `Comando "${command}" enviado — se ejecutará en el próximo heartbeat (≤30s)` })
            onDone?.()
        } catch {
            setFeedback({ ok: false, text: 'Error al enviar el comando' })
        } finally {
            setLoading(null)
        }
    }

    const CMDS = [
        { cmd: 'lock', label: '🔒 Bloquear pantalla', cls: 'btn-ghost' },
        { cmd: 'alarm', label: '🔊 Activar alarma', cls: 'btn-warn' },
        { cmd: 'shutdown', label: '⏻ Apagar tablet', cls: 'btn-danger' },
    ]

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {CMDS.map(({ cmd, label, cls }) => (
                    <button
                        key={cmd}
                        className={cls}
                        disabled={!!loading}
                        onClick={() => send(cmd)}
                        style={{ opacity: loading && loading !== cmd ? 0.5 : 1 }}
                    >
                        {loading === cmd ? '...' : label}
                    </button>
                ))}

                {/* Mensaje personalizado */}
                {!showMsg ? (
                    <button className="btn-ghost" onClick={() => setShowMsg(true)}>
                        💬 Enviar mensaje
                    </button>
                ) : (
                    <div style={{ display: 'flex', gap: '6px', width: '100%' }}>
                        <input
                            placeholder="Escribe el mensaje para la tablet..."
                            value={message}
                            onChange={e => setMessage(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && message && send('message', { message })}
                            autoFocus
                        />
                        <button
                            className="btn-primary"
                            disabled={!message || !!loading}
                            onClick={() => send('message', { message })}
                            style={{ whiteSpace: 'nowrap' }}
                        >
                            {loading === 'message' ? '...' : 'Enviar'}
                        </button>
                        <button className="btn-ghost" onClick={() => setShowMsg(false)}>✕</button>
                    </div>
                )}
            </div>

            {feedback && (
                <div style={{
                    padding: '8px 12px',
                    borderRadius: 'var(--radius)',
                    background: feedback.ok ? 'var(--green-dim)' : 'var(--red-dim)',
                    color: feedback.ok ? 'var(--green)' : 'var(--red)',
                    fontSize: '12px',
                    fontFamily: 'var(--font-mono)',
                }}>
                    {feedback.text}
                </div>
            )}
        </div>
    )
}