import { useEffect, useRef, useCallback } from 'react'

const WS_URL = import.meta.env.VITE_WS_URL || `ws://${window.location.host}/ws`

/**
 * Hook que mantiene una conexión WebSocket con el backend.
 * Se reconecta automáticamente si se pierde la conexión.
 *
 * @param {(event: string, data: object) => void} onMessage
 */
export function useWebSocket(onMessage) {
    const wsRef = useRef(null)
    const retryRef = useRef(null)
    const onMsgRef = useRef(onMessage)
    onMsgRef.current = onMessage

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return

        try {
            const ws = new WebSocket(WS_URL)

            ws.onopen = () => {
                console.log('[WS] Conectado al servidor')
                if (retryRef.current) {
                    clearTimeout(retryRef.current)
                    retryRef.current = null
                }
            }

            ws.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data)
                    if (data.event !== 'ping') {
                        onMsgRef.current?.(data.event, data)
                    }
                } catch { /* ignorar mensajes malformados */ }
            }

            ws.onclose = () => {
                console.log('[WS] Desconectado — reintentando en 5s...')
                retryRef.current = setTimeout(connect, 5000)
            }

            ws.onerror = () => {
                ws.close()
            }

            wsRef.current = ws
        } catch (err) {
            console.warn('[WS] No se pudo conectar:', err)
            retryRef.current = setTimeout(connect, 5000)
        }
    }, [])

    useEffect(() => {
        connect()
        return () => {
            clearTimeout(retryRef.current)
            wsRef.current?.close()
        }
    }, [connect])
}