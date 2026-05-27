import React, { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { getRoomStatus } from '../api/rooms'
import { useGame } from '../context/GameContext'

export default function ActiveGameBanner() {
  const { state, reset } = useGame()
  const navigate = useNavigate()
  const location = useLocation()
  const [visible, setVisible] = useState(false)
  const [roomPhase, setRoomPhase] = useState(null)
  const [dismissed, setDismissed] = useState(false)

  const roomCode = state.roomCode
  const playerId = state.playerId

  useEffect(() => {
    if (!roomCode || !playerId || dismissed) {
      setVisible(false)
      return
    }
    getRoomStatus(roomCode)
      .then(r => {
        if (r.data.status === 'finished') {
          reset()
          setVisible(false)
        } else {
          setRoomPhase(r.data.status)
          setVisible(true)
        }
      })
      .catch(() => {
        reset()
        setVisible(false)
      })
  }, [roomCode, playerId, dismissed])

  const isOnCurrentRoom = roomCode && (
    location.pathname.startsWith(`/game/${roomCode}`) ||
    location.pathname.startsWith(`/lobby/${roomCode}`)
  )

  if (!visible || isOnCurrentRoom || dismissed) return null

  const handleJoin = () => {
    const path = roomPhase === 'playing' ? `/game/${roomCode}` : `/lobby/${roomCode}`
    navigate(path)
  }

  const phaseLabel = roomPhase === 'playing' ? 'Игра идёт' : 'Лобби'
  const phaseColor = roomPhase === 'playing' ? 'var(--green)' : 'var(--purple-light)'

  return (
    <>
      <style>{`
        @keyframes bannerSlideIn {
          from { transform: translateX(-120%); opacity: 0; }
          to   { transform: translateX(0);    opacity: 1; }
        }
        .active-game-banner { animation: bannerSlideIn 0.35s cubic-bezier(0.34,1.56,0.64,1) both; }
      `}</style>
      <div
        className="active-game-banner active-banner-mobile"
        style={{
          position: 'fixed',
          bottom: 24,
          left: 24,
          zIndex: 9999,
          background: 'var(--bg-1)',
          border: '1.5px solid var(--purple)',
          borderRadius: 16,
          padding: '12px 14px',
          boxShadow: '0 8px 32px var(--purple-glow), 0 2px 8px rgba(0,0,0,0.3)',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          minWidth: 250,
          maxWidth: 320,
        }}
      >
        <div style={{
          width: 38, height: 38, borderRadius: 10, flexShrink: 0,
          background: 'linear-gradient(135deg, var(--purple), var(--pink))',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 11, fontWeight: 900, letterSpacing: '-0.5px', color: '#fff',
        }}>
          MB
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 5, marginBottom: 2,
          }}>
            <div style={{
              width: 6, height: 6, borderRadius: '50%',
              background: phaseColor, boxShadow: `0 0 6px ${phaseColor}`,
              animation: 'glowPulse 2s ease infinite',
            }} />
            <span style={{ fontSize: 10, fontWeight: 700, color: phaseColor, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              {phaseLabel}
            </span>
          </div>
          <div style={{ fontFamily: "'Space Grotesk',sans-serif", fontWeight: 800, fontSize: 16, letterSpacing: 2 }}>
            {roomCode}
          </div>
        </div>

        <button
          onClick={handleJoin}
          style={{
            background: 'linear-gradient(135deg, var(--purple), var(--pink))',
            border: 'none', borderRadius: 10, padding: '7px 13px',
            color: '#fff', fontWeight: 700, fontSize: 12,
            cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0,
            fontFamily: "'Space Grotesk',sans-serif",
          }}
        >
          Войти
        </button>

        <button
          onClick={() => setDismissed(true)}
          style={{
            background: 'none', border: 'none', color: 'var(--text-3)',
            cursor: 'pointer', padding: '2px 4px', fontSize: 18,
            lineHeight: 1, borderRadius: 6, flexShrink: 0,
            transition: 'color 0.15s',
          }}
          onMouseEnter={e => e.target.style.color = 'var(--text)'}
          onMouseLeave={e => e.target.style.color = 'var(--text-3)'}
        >
          ×
        </button>
      </div>
    </>
  )
}
