import { useEffect, useRef, useCallback } from 'react'
import { useGame } from '../context/GameContext'

export default function useGameSocket(roomCode, playerId) {
  const { handleWsMessage } = useGame()
  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)

  const activeRef = useRef(false)

  const connect = useCallback(() => {
    if (!roomCode || !playerId) return

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${protocol}://${window.location.host}/ws/${roomCode}/${playerId}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        handleWsMessage(msg)
      } catch (_) {}
    }

    ws.onclose = () => {
      if (activeRef.current) {
        reconnectTimer.current = setTimeout(connect, 2000)
      }
    }

    ws.onerror = () => ws.close()
  }, [roomCode, playerId, handleWsMessage])

  useEffect(() => {
    activeRef.current = true
    connect()
    return () => {
      activeRef.current = false
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [connect])

  const send = useCallback((type, payload = {}) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, payload }))
    }
  }, [])

  return { send }
}
