import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login, setToken } from '../api'

export default function Login() {
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()

    const handleSubmit = async (e) => {
        e.preventDefault()
        setError('')
        setLoading(true)
        try {
            const res = await login(password)
            setToken(res.access_token)
            navigate('/')
        } catch {
            setError('Contraseña incorrecta')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'var(--bg-base)',
        }}>
            {/* Grid de fondo decorativo */}
            <div style={{
                position: 'fixed', inset: 0, pointerEvents: 'none',
                backgroundImage: `
          linear-gradient(var(--border) 1px, transparent 1px),
          linear-gradient(90deg, var(--border) 1px, transparent 1px)
        `,
                backgroundSize: '40px 40px',
                opacity: 0.3,
            }} />

            <div className="card fade-in" style={{ width: '360px', position: 'relative' }}>
                {/* Header */}
                <div style={{ marginBottom: '28px', textAlign: 'center' }}>
                    <div style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '11px',
                        color: 'var(--blue)',
                        letterSpacing: '0.2em',
                        marginBottom: '8px',
                    }}>
                        TABLET MONITOR
                    </div>
                    <h1 style={{ fontSize: '22px', fontWeight: 600, color: 'var(--text-primary)' }}>
                        Panel de Control
                    </h1>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginTop: '4px' }}>
                        Acceso restringido — solo administradores
                    </p>
                </div>

                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    <div>
                        <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '6px', fontFamily: 'var(--font-mono)' }}>
                            CONTRASEÑA
                        </label>
                        <input
                            type="password"
                            placeholder="••••••••"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            autoFocus
                        />
                    </div>

                    {error && (
                        <div style={{ color: 'var(--red)', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>
                            ⚠ {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        className="btn-primary"
                        disabled={loading || !password}
                        style={{ justifyContent: 'center', padding: '10px', marginTop: '4px' }}
                    >
                        {loading ? 'Verificando...' : 'Ingresar →'}
                    </button>
                </form>
            </div>
        </div>
    )
}