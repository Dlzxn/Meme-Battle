import React, { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import PlayerList from '../components/PlayerList'
import Toast from '../components/Toast'
import useToast from '../hooks/useToast'
import useGameSocket from '../hooks/useGameSocket'
import { useGame } from '../context/GameContext'
import { kickPlayer } from '../api/rooms'

export default function LobbyPage() {
  const { code } = useParams()
  const navigate = useNavigate()
  const { state, setRoom } = useGame()
  const { toasts, addToast } = useToast()

  useEffect(() => {
    if (!state.roomCode) {
      const sc = sessionStorage.getItem('roomCode')
      const si = sessionStorage.getItem('playerId')
      if (sc === code && si) setRoom(code, parseInt(si))
    }
  }, [code, state.roomCode, setRoom])

  useEffect(() => {
    if (state.roomCode) {
      sessionStorage.setItem('roomCode', state.roomCode)
      sessionStorage.setItem('playerId', state.playerId)
    }
  }, [state.roomCode, state.playerId])

  const { send } = useGameSocket(state.roomCode || code, state.playerId)

  useEffect(() => {
    if (state.phase === 'playing' && state.situation !== null) navigate(`/game/${code}`)
  }, [state.phase, state.situation, code, navigate])

  const connected = state.players.filter(p => p.is_connected)
  const canStart  = connected.length >= 2

  const handleStart = () => {
    if (!canStart) { addToast('Нужно минимум 2 игрока', 'error'); return }
    send('start_game')
  }

  const handleKick = async (pid) => {
    try { await kickPlayer(code, pid) }
    catch { addToast('Ошибка', 'error') }
  }

  return (
    <div className="page">
      <Navbar />

      <div className="container" style={{ paddingTop: 48, paddingBottom: 60, flex: 1 }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 40, flexWrap: 'wrap', gap: 20 }}>
          <div>
            <div style={{ display:'inline-flex', alignItems:'center', gap:8, background:'rgba(139,92,246,0.12)', border:'1px solid rgba(139,92,246,0.25)', borderRadius:20, padding:'4px 14px', fontSize:12, fontWeight:700, color:'var(--purple-light)', textTransform:'uppercase', letterSpacing:'0.1em', marginBottom:16 }}>
              <div className="glow-dot purple" />
              Лобби · ожидание игроков
            </div>
            <h1 style={{ fontSize: 36, fontWeight: 800, marginBottom: 12 }}>Комната готова</h1>
            <p style={{ color: 'var(--text-2)', marginBottom: 16 }}>Поделись кодом — и начинайте</p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div
                className="room-code"
                onClick={() => { navigator.clipboard.writeText(code); addToast('📋 Код скопирован!', 'success') }}
                title="Нажми чтобы скопировать"
              >
                {code}
              </div>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => { navigator.clipboard.writeText(code); addToast('📋 Скопировано!', 'success') }}
              >
                📋 Копировать
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, alignItems: 'flex-end' }}>
            {/* Player dots */}
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} style={{
                  width: i < connected.length ? 12 : 8,
                  height: i < connected.length ? 12 : 8,
                  borderRadius: '50%',
                  background: i < connected.length ? 'var(--purple)' : 'var(--glass-border)',
                  boxShadow: i < connected.length ? '0 0 10px var(--purple)' : 'none',
                  transition: 'all 0.3s cubic-bezier(0.34,1.56,0.64,1)',
                }} />
              ))}
              <span style={{ fontSize: 13, color: 'var(--text-3)', marginLeft: 4 }}>
                {connected.length}/8
              </span>
            </div>
            {!canStart && (
              <div style={{ fontSize: 12, color: 'var(--yellow-light)', background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: 8, padding: '4px 12px' }}>
                ⚠️ Нужен ещё 1 игрок
              </div>
            )}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 24, alignItems: 'start' }}>
          {/* Players */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
              <h3 style={{ fontWeight: 700, fontSize: 16, color: 'var(--text-2)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Игроки
              </h3>
              <span style={{ fontSize: 13, color: 'var(--text-3)' }}>{connected.length} онлайн</span>
            </div>
            <PlayerList
              players={state.players}
              currentPlayerId={state.playerId}
              isHost={state.isHost}
              onKick={handleKick}
            />
          </div>

          {/* Sidebar */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {state.isHost ? (
              <div>
                <button
                  className="btn btn-primary w-full"
                  style={{ padding: '18px 24px', fontSize: 16 }}
                  onClick={handleStart}
                  disabled={!canStart}
                >
                  {canStart ? '🚀 Начать игру' : `⏳ Ждём игроков (${connected.length}/2)`}
                </button>
                {canStart && (
                  <p style={{ fontSize: 12, color: 'var(--text-3)', textAlign: 'center', marginTop: 8 }}>
                    {connected.length} игроков готовы к бою
                  </p>
                )}
              </div>
            ) : (
              <div className="glass" style={{ padding: 20, textAlign: 'center' }}>
                <div style={{ fontSize: 32, marginBottom: 8 }}>⏳</div>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>Ожидаем хоста</div>
                <div style={{ fontSize: 13, color: 'var(--text-3)' }}>Хост запустит игру</div>
              </div>
            )}

            {/* Tips */}
            <div className="glass" style={{ padding: 20 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 14 }}>
                🃏 Правила
              </div>
              {[
                ['Сыграй мем', 'Выбери карту на ситуацию'],
                ['Голосуй', 'Выбери лучший ответ'],
                ['Победи раунд', 'Скинь карту и наблюдай'],
                ['Проиграй раунд', 'Получи штрафные карты'],
                ['Избавься от всех', 'Ты победитель!'],
              ].map(([t, d]) => (
                <div key={t} style={{ display:'flex', gap:10, marginBottom:10, alignItems:'flex-start' }}>
                  <div className="glow-dot purple" style={{ marginTop: 6, flexShrink: 0 }} />
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{t}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-3)' }}>{d}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <Toast toasts={toasts} />
    </div>
  )
}
