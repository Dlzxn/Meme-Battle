import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import PlayerList from '../components/PlayerList'
import Toast from '../components/Toast'
import useToast from '../hooks/useToast'
import useGameSocket from '../hooks/useGameSocket'
import { useGame } from '../context/GameContext'
import { kickPlayer } from '../api/rooms'

const MODES = [
  { value: 'no_czar', label: 'Без ведущего' },
  { value: 'czar',    label: 'С ведущим'    },
  { value: 'arena',   label: 'Арена'         },
]
const CATEGORIES = [
  { value: 'all',       label: 'Всё'        },
  { value: 'work',      label: 'Работа'     },
  { value: 'school',    label: 'Школа'      },
  { value: 'relations', label: 'Отношения'  },
  { value: 'internet',  label: 'Интернет'   },
]

export default function LobbyPage() {
  const { code } = useParams()
  const navigate = useNavigate()
  const { state, setRoom } = useGame()
  const { toasts, addToast } = useToast()
  const [configOpen, setConfigOpen] = useState(false)
  const [localConfig, setLocalConfig] = useState(null)

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

  useEffect(() => {
    if (state.roomConfig && !localConfig) {
      setLocalConfig(state.roomConfig)
    }
  }, [state.roomConfig])

  const { send } = useGameSocket(state.roomCode || code, state.playerId)

  const copyCode = () => {
    const fallback = () => {
      const el = document.createElement('textarea')
      el.value = code
      el.style.cssText = 'position:fixed;top:0;left:0;opacity:0;pointer-events:none;'
      document.body.appendChild(el)
      el.focus(); el.select()
      try { document.execCommand('copy'); addToast('Скопировано', 'success') }
      catch { addToast('Не удалось скопировать', 'error') }
      document.body.removeChild(el)
    }
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(code).then(() => addToast('Скопировано', 'success')).catch(fallback)
    } else {
      fallback()
    }
  }

  // Track if game_started fired while on this page (not a reconnect to ongoing game)
  const gameStartingRef = React.useRef(false)
  useEffect(() => {
    if (state.gameJustStarted) gameStartingRef.current = true
  }, [state.gameJustStarted])
  useEffect(() => {
    if (gameStartingRef.current && state.situation !== null) navigate(`/game/${code}`)
  }, [state.situation, code, navigate])

  useEffect(() => {
    if (state.roomCode === null) {
      addToast('Комната закрыта', 'info')
      navigate('/')
    }
  }, [state.roomCode])

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

  const updateConfig = (key, value) => {
    const next = { ...localConfig, [key]: value }
    setLocalConfig(next)
    send('update_config', { [key]: value })
  }

  const cfg = localConfig || state.roomConfig || {}

  return (
    <div className="page">
      <Navbar />

      <div className="container page-content-mobile" style={{ paddingTop: 36, paddingBottom: 48, flex: 1 }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 32, flexWrap: 'wrap', gap: 16 }}>
          <div>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: 'rgba(139,92,246,0.12)', border: '1px solid rgba(139,92,246,0.25)', borderRadius: 20, padding: '4px 14px', fontSize: 12, fontWeight: 700, color: 'var(--purple-light)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 14 }}>
              <div className="glow-dot purple" />
              Лобби · ожидание игроков
            </div>
            <h1 style={{ fontSize: 'clamp(24px, 5vw, 36px)', fontWeight: 800, marginBottom: 10 }}>Комната готова</h1>
            <p style={{ color: 'var(--text-2)', marginBottom: 14 }}>Поделись кодом — и начинайте</p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <div
                className="room-code"
                onClick={copyCode}
                title="Нажми чтобы скопировать"
              >
                {code}
              </div>
              <button
                className="btn btn-ghost btn-sm"
                onClick={copyCode}
              >
                Копировать
              </button>
            </div>
          </div>

          {state.phase === 'playing' && (
            <button
              className="btn btn-primary"
              style={{ padding: '11px 22px', fontSize: 14 }}
              onClick={() => navigate(`/game/${code}`)}
            >
              Войти в игру
            </button>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'flex-end' }}>
            <div style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} style={{
                  width: i < connected.length ? 11 : 7,
                  height: i < connected.length ? 11 : 7,
                  borderRadius: '50%',
                  background: i < connected.length ? 'var(--purple)' : 'var(--glass-border)',
                  boxShadow: i < connected.length ? '0 0 10px var(--purple)' : 'none',
                  transition: 'all 0.3s cubic-bezier(0.34,1.56,0.64,1)',
                }} />
              ))}
              <span style={{ fontSize: 13, color: 'var(--text-3)', marginLeft: 4 }}>{connected.length}/8</span>
            </div>
            {!canStart && (
              <div style={{ fontSize: 12, color: 'var(--yellow-light)', background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: 8, padding: '4px 12px' }}>
                Нужен ещё 1 игрок
              </div>
            )}
          </div>
        </div>

        <div className="lobby-grid">
          {/* Players */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <h3 style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-2)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
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

            {/* Config panel for host */}
            {state.isHost && (
              <div style={{ marginTop: 20 }}>
                <button
                  className="btn btn-ghost w-full"
                  style={{ justifyContent: 'space-between', padding: '11px 14px' }}
                  onClick={() => setConfigOpen(v => !v)}
                >
                  <span>Настройки комнаты</span>
                  <span style={{ fontSize: 11, color: 'var(--text-3)' }}>{configOpen ? '▲ Свернуть' : '▼ Развернуть'}</span>
                </button>

                {configOpen && localConfig && (
                  <div className="glass" style={{ padding: 18, marginTop: 8 }}>
                    <div className="settings-grid">

                      <div className="form-group" style={{ marginBottom: 0 }}>
                        <label>Режим</label>
                        <select className="input" value={cfg.mode || 'no_czar'} onChange={e => updateConfig('mode', e.target.value)}>
                          {MODES.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                        </select>
                      </div>

                      <div className="form-group" style={{ marginBottom: 0 }}>
                        <label>Категория</label>
                        <select className="input" value={cfg.category || 'all'} onChange={e => updateConfig('category', e.target.value)}>
                          {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                        </select>
                      </div>

                      <div className="form-group" style={{ marginBottom: 0 }}>
                        <label>Таймер хода</label>
                        <select className="input" value={cfg.timer_play || 60} onChange={e => updateConfig('timer_play', +e.target.value)}>
                          {[15, 30, 45, 60, 75, 90, 105, 120].map(t => <option key={t} value={t}>{t} сек</option>)}
                        </select>
                      </div>

                      <div className="form-group" style={{ marginBottom: 0 }}>
                        <label>Таймер голосования</label>
                        <select className="input" value={cfg.timer_vote || 30} onChange={e => updateConfig('timer_vote', +e.target.value)}>
                          {[15, 30, 45, 60].map(t => <option key={t} value={t}>{t} сек</option>)}
                        </select>
                      </div>

                      <div className="form-group" style={{ marginBottom: 0 }}>
                        <label>Карт в руке</label>
                        <select className="input" value={cfg.cards_count || 7} onChange={e => updateConfig('cards_count', +e.target.value)}>
                          {[5, 6, 7, 8, 9, 10].map(n => <option key={n} value={n}>{n} карт</option>)}
                        </select>
                      </div>

                      {cfg.mode !== 'arena' ? (
                        <div className="form-group" style={{ marginBottom: 0 }}>
                          <label>Штраф</label>
                          <select className="input" value={cfg.penalty_count || 1} onChange={e => updateConfig('penalty_count', +e.target.value)}>
                            <option value={1}>1 карта</option>
                            <option value={2}>2 карты</option>
                          </select>
                        </div>
                      ) : (
                        <div className="form-group" style={{ marginBottom: 0 }}>
                          <label>Раундов</label>
                          <select className="input" value={cfg.rounds_count || 10} onChange={e => updateConfig('rounds_count', +e.target.value)}>
                            {[5, 8, 10, 15, 20].map(n => <option key={n} value={n}>{n}</option>)}
                          </select>
                        </div>
                      )}

                      <div className="form-group" style={{ marginBottom: 0, gridColumn: '1 / -1' }}>
                        <label>Тип</label>
                        <div style={{ display: 'flex', gap: 8 }}>
                          {[{ v: false, l: 'Приват' }, { v: true, l: 'Публичная' }].map(o => (
                            <button key={String(o.v)} onClick={() => updateConfig('is_public', o.v)} style={{
                              flex: 1, padding: '9px 10px', borderRadius: 10, border: '1.5px solid',
                              borderColor: cfg.is_public === o.v ? 'var(--purple)' : 'var(--glass-border)',
                              background: cfg.is_public === o.v ? 'var(--purple-dim)' : 'var(--glass)',
                              cursor: 'pointer', fontWeight: 700, fontSize: 13,
                              color: cfg.is_public === o.v ? 'var(--purple-light)' : 'var(--text-2)',
                              transition: 'all 0.15s',
                            }}>
                              {o.l}
                            </button>
                          ))}
                        </div>
                      </div>

                      <div className="form-group" style={{ marginBottom: 0, gridColumn: '1 / -1' }}>
                        <label>Свои ситуации (по одной на строку)</label>
                        <textarea
                          className="input"
                          rows={3}
                          value={cfg.custom_situations || ''}
                          onChange={e => updateConfig('custom_situations', e.target.value || null)}
                          placeholder="Менеджер просит маленькую правку..."
                        />
                      </div>
                    </div>

                    <div style={{ marginTop: 10, fontSize: 12, color: 'var(--green-light)', display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green)', boxShadow: '0 0 6px var(--green)', display: 'inline-block', flexShrink: 0 }} />
                      Изменения применяются сразу для всех
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {state.isHost ? (
              <div>
                <button
                  className="btn btn-primary w-full"
                  style={{ padding: '16px 24px', fontSize: 16 }}
                  onClick={handleStart}
                  disabled={!canStart}
                >
                  {canStart ? 'Начать игру' : `Ждём игроков (${connected.length}/2)`}
                </button>
                {canStart && (
                  <p style={{ fontSize: 12, color: 'var(--text-3)', textAlign: 'center', marginTop: 8 }}>
                    {connected.length} игроков готовы
                  </p>
                )}
              </div>
            ) : (
              <div className="glass" style={{ padding: 18, textAlign: 'center' }}>
                <div style={{
                  width: 36, height: 36, borderRadius: 10, margin: '0 auto 10px',
                  background: 'var(--purple-dim)', border: '1.5px solid var(--glass-border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                </div>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>Ожидаем хоста</div>
                <div style={{ fontSize: 13, color: 'var(--text-3)' }}>
                  {cfg.mode === 'arena' ? 'Режим Арена' : cfg.mode === 'czar' ? 'Режим с ведущим' : 'Режим голосования'}
                </div>
              </div>
            )}

            {/* Game info */}
            {Object.keys(cfg).length > 0 && (
              <div className="glass" style={{ padding: 14 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 10 }}>
                  Настройки игры
                </div>
                {[
                  ['Режим', MODES.find(m => m.value === cfg.mode)?.label || cfg.mode],
                  ['Таймер хода', `${cfg.timer_play} сек`],
                  ['Таймер голосования', `${cfg.timer_vote} сек`],
                  ['Карт в руке', cfg.cards_count],
                  cfg.mode === 'arena'
                    ? ['Раундов', cfg.rounds_count]
                    : ['Штраф', `${cfg.penalty_count} карта`],
                ].map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 7, fontSize: 13 }}>
                    <span style={{ color: 'var(--text-3)' }}>{k}</span>
                    <span style={{ fontWeight: 600 }}>{v}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Rules */}
            <div className="glass" style={{ padding: 18 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>
                {cfg.mode === 'arena' ? 'Арена' : 'Правила'}
              </div>
              {(cfg.mode === 'arena' ? [
                ['Каждый раунд', `${cfg.cards_count || 7} новых карт`],
                ['Голосуй', 'Выбери лучший мем'],
                ['Считаем голоса', 'За каждый раунд'],
                ['Победитель', 'Больше всего голосов'],
              ] : [
                ['Сыграй мем', 'Выбери карту на ситуацию'],
                ['Голосуй', 'Выбери лучший ответ'],
                ['Победи раунд', 'Скинь карту и наблюдай'],
                ['Проиграй раунд', 'Получи штрафные карты'],
                ['Избавься от всех', 'Ты победитель!'],
              ]).map(([t, d]) => (
                <div key={t} style={{ display: 'flex', gap: 10, marginBottom: 9, alignItems: 'flex-start' }}>
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
