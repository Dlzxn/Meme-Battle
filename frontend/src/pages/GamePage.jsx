import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import MemeCard from '../components/MemeCard'
import PlayerList from '../components/PlayerList'
import Timer from '../components/Timer'
import Toast from '../components/Toast'
import useToast from '../hooks/useToast'
import useGameSocket from '../hooks/useGameSocket'
import { useGame } from '../context/GameContext'

const REACTIONS = [
  { type: 'laugh', emoji: '😂', label: 'Лол'   },
  { type: 'fire',  emoji: '🔥', label: 'Огонь' },
  { type: 'trash', emoji: '🗑', label: 'Мусор' },
]

export default function GamePage() {
  const { code } = useParams()
  const navigate = useNavigate()
  const { state, setRoom, playCardLocal, dispatch } = useGame()
  const { toasts, addToast } = useToast()
  const [selectedCard, setSelectedCard] = useState(null)
  const [myReactions, setMyReactions] = useState({})

  useEffect(() => {
    if (!state.roomCode) {
      const sc = sessionStorage.getItem('roomCode')
      const si = sessionStorage.getItem('playerId')
      if (sc === code && si) setRoom(code, parseInt(si))
    }
  }, [code, state.roomCode, setRoom])

  const { send } = useGameSocket(state.roomCode || code, state.playerId)

  useEffect(() => {
    if (state.phase === 'lobby' && state.roomCode === null) {
      addToast('Комната закрыта', 'info')
      setTimeout(() => navigate('/'), 2000)
    }
  }, [state.roomCode])

  const alreadyPlayed = state.playedIds.has(state.playerId)

  const handlePlayCard = () => {
    if (!selectedCard || alreadyPlayed) return
    send('play_card', { card_id: selectedCard })
    playCardLocal(selectedCard)
    setSelectedCard(null)
    addToast('Карта сыграна', 'success')
  }

  const handleVote = (play) => {
    if (play.player_id === state.playerId || state.votedThisRound) return
    send('vote', { target_player_id: play.player_id, play_id: play.play_id })
    dispatch({ type: 'VOTE_CAST', voter_id: state.playerId })
    addToast('Голос отдан', 'success')
  }

  const handleReaction = (playId, type) => {
    if (myReactions[playId]) return
    send('add_reaction', { play_id: playId, reaction_type: type })
    setMyReactions(p => ({ ...p, [playId]: type }))
  }

  const handleCzarPick = (play) => {
    send('czar_pick', { winner_player_id: play.player_id })
    addToast('Победитель выбран', 'success')
  }

  if (state.phase === 'game_over') {
    return <GameOverScreen gameOver={state.gameOver} playerId={state.playerId} onExit={() => navigate('/')} />
  }

  const [loadStuck, setLoadStuck] = useState(false)
  useEffect(() => {
    if (!state.situation && state.phase !== 'results' && state.phase !== 'game_over') {
      const t = setTimeout(() => setLoadStuck(true), 12000)
      return () => clearTimeout(t)
    }
    setLoadStuck(false)
  }, [state.situation, state.phase])

  if (!state.situation && state.phase !== 'results') {
    return (
      <div className="page">
        <Navbar />
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 16 }}>
          {loadStuck ? (
            <>
              <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-2)' }}>Не удаётся загрузить раунд</div>
              <div style={{ fontSize: 13, color: 'var(--text-3)' }}>Игра могла завершиться или соединение потеряно</div>
              <button className="btn btn-primary" onClick={() => navigate('/')}>На главную</button>
            </>
          ) : (
            <>
              <div className="spinner" style={{ width: 48, height: 48 }} />
              <div style={{ color: 'var(--text-3)' }}>Загружаем раунд...</div>
            </>
          )}
        </div>
      </div>
    )
  }

  const phaseInfo = {
    playing: { label: 'Ход',          cls: 'play'   },
    voting:  { label: 'Голосование',  cls: 'vote'   },
    results: { label: 'Результаты',   cls: 'result' },
  }[state.phase] || { label: '...', cls: 'play' }

  return (
    <div className="page" style={{ background: 'var(--bg)' }}>
      <Navbar />

      {/* TOP BAR */}
      <div style={{
        background: 'rgba(7,7,15,0.9)',
        borderBottom: '1px solid var(--glass-border)',
        backdropFilter: 'blur(20px)',
        padding: '10px 16px',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className={`phase-banner ${phaseInfo.cls}`}>
            {phaseInfo.label}
          </span>
          <span style={{ fontSize: 13, color: 'var(--text-3)' }}>
            Раунд {state.roundNumber}
            {state.roundsTotal > 1 && state.roomConfig?.mode === 'arena' && (
              <span style={{ color: 'var(--purple-light)' }}> / {state.roundsTotal}</span>
            )}
          </span>
        </div>
        <div style={{ flex: 1 }} />
        {state.isCzar && (
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.25)', borderRadius: 20, padding: '4px 12px', fontSize: 12, fontWeight: 700, color: 'var(--yellow-light)' }}>
            Ведущий
          </div>
        )}
        <Timer seconds={state.timer} total={state.timerTotal || 60} />
      </div>

      <div className="container page-content-mobile" style={{ paddingTop: 24, paddingBottom: 36, flex: 1 }}>
        <div className="game-grid">

          {/* MAIN */}
          <div style={{ minWidth: 0 }}>

            {/* SITUATION */}
            {state.situation && (
              <div className="situation-card" style={{ marginBottom: 24 }}>
                <div className="situation-card-label">Ситуация</div>
                <div className="situation-card-text">{state.situation}</div>
              </div>
            )}

            {/* PLAY PHASE */}
            {state.phase === 'playing' && (
              <>
                {state.isCzar ? (
                  <div className="glass" style={{ padding: 'clamp(24px, 6vw, 48px)', textAlign: 'center' }}>
                    <div style={{ width: 52, height: 52, borderRadius: 14, background: 'rgba(245,158,11,0.12)', border: '1.5px solid rgba(245,158,11,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 14px', fontSize: 11, fontWeight: 800, letterSpacing: '0.08em', color: 'var(--yellow-light)', textTransform: 'uppercase' }}>
                      Czar
                    </div>
                    <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>Вы ведущий этого раунда</h3>
                    <p style={{ color: 'var(--text-2)', fontSize: 14 }}>Ожидайте ответы игроков — затем выберете победителя</p>
                  </div>
                ) : alreadyPlayed ? (
                  <div className="glass" style={{ padding: 'clamp(24px, 6vw, 48px)', textAlign: 'center' }}>
                    <div style={{ width: 52, height: 52, borderRadius: 14, background: 'rgba(5,150,105,0.12)', border: '1.5px solid rgba(5,150,105,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 14px', fontSize: 22, color: 'var(--green-light)' }}>
                      ✓
                    </div>
                    <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>Карта сыграна</h3>
                    <p style={{ color: 'var(--text-2)', marginBottom: 20, fontSize: 14 }}>Ждём остальных игроков...</p>
                    <div style={{ display: 'flex', justifyContent: 'center', gap: 8, flexWrap: 'wrap' }}>
                      {state.players.filter(p => p.is_connected).map(p => (
                        <div key={p.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                          <div style={{
                            width: 34, height: 34, borderRadius: 9, display: 'flex', alignItems: 'center', justifyContent: 'center',
                            background: state.playedIds.has(p.id) ? 'linear-gradient(135deg,var(--green),#059669)' : 'var(--glass)',
                            border: `1.5px solid ${state.playedIds.has(p.id) ? 'var(--green)' : 'var(--glass-border)'}`,
                            fontSize: 13, fontWeight: 800, transition: 'all 0.3s',
                            boxShadow: state.playedIds.has(p.id) ? '0 0 12px var(--green-glow)' : 'none',
                            color: state.playedIds.has(p.id) ? '#fff' : 'var(--text-2)',
                          }}>
                            {state.playedIds.has(p.id) ? '✓' : p.nickname[0].toUpperCase()}
                          </div>
                          <div style={{ fontSize: 10, color: 'var(--text-3)' }}>
                            {state.playedIds.has(p.id) ? 'готов' : '...'}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14, gap: 10, flexWrap: 'wrap' }}>
                      <div>
                        <h3 style={{ fontWeight: 700, fontSize: 17 }}>Твоя рука</h3>
                        <p style={{ fontSize: 13, color: 'var(--text-3)', marginTop: 2 }}>
                          {state.myCards.length} карт · {selectedCard ? 'Нажми «Сыграть»' : 'Выбери мем'}
                        </p>
                      </div>
                      <button
                        className="btn btn-primary"
                        onClick={handlePlayCard}
                        disabled={!selectedCard}
                        style={{ padding: '11px 24px', flexShrink: 0 }}
                      >
                        Сыграть карту
                      </button>
                    </div>
                    <div className="hand-grid">
                      {state.myCards.map(card => (
                        <MemeCard
                          key={card.card_id}
                          card={card}
                          selected={selectedCard === card.card_id}
                          onClick={() => setSelectedCard(selectedCard === card.card_id ? null : card.card_id)}
                        />
                      ))}
                    </div>
                    {state.myCards.length === 0 && (
                      <div className="glass" style={{ padding: 32, textAlign: 'center', color: 'var(--text-3)' }}>
                        Нет карт — ожидайте следующего раунда
                      </div>
                    )}
                  </>
                )}
              </>
            )}

            {/* VOTING PHASE */}
            {state.phase === 'voting' && (
              <>
                <div style={{ marginBottom: 18 }}>
                  <h3 style={{ fontWeight: 700, fontSize: 17 }}>
                    {state.isCzar ? 'Выберите лучший мем' : 'Голосуйте за лучший мем'}
                  </h3>
                  <p style={{ fontSize: 13, color: 'var(--text-3)', marginTop: 4 }}>
                    {state.isCzar ? 'Вы выбираете победителя раунда' : 'Нельзя голосовать за себя'}
                  </p>
                </div>
                <div className="plays-grid">
                  {state.plays.map(play => {
                    const isMine   = play.player_id === state.playerId
                    const reaction = myReactions[play.play_id]
                    const voted    = state.votedThisRound
                    return (
                      <div key={play.play_id} className={`voting-card ${!isMine && voted ? 'voted' : ''}`}>
                        <div style={{ position: 'relative', overflow: 'hidden' }}>
                          <img
                            src={play.meme_url} alt={play.meme_name}
                            referrerPolicy="no-referrer"
                            style={{ width: '100%', aspectRatio: '1', objectFit: 'cover', display: 'block' }}
                          />
                          {play.second_meme_url && (
                            <img
                              src={play.second_meme_url} alt="Second"
                              referrerPolicy="no-referrer"
                              style={{ width: '100%', aspectRatio: '1', objectFit: 'cover', display: 'block', borderTop: '2px solid var(--glass-border)' }}
                            />
                          )}
                          {isMine && (
                            <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', backdropFilter: 'blur(2px)' }}>
                              <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-2)', background: 'rgba(0,0,0,0.6)', padding: '5px 12px', borderRadius: 8 }}>
                                Ваш мем
                              </span>
                            </div>
                          )}
                        </div>
                        <div style={{ padding: 12 }}>
                          <div style={{ fontSize: 12, color: 'var(--text-3)', marginBottom: 9, fontWeight: 600 }}>
                            {play.meme_name}
                          </div>
                          <div style={{ display: 'flex', gap: 5, marginBottom: 10 }}>
                            {REACTIONS.map(r => (
                              <button key={r.type}
                                className={`reaction-btn ${reaction === r.type ? 'active' : ''}`}
                                onClick={() => handleReaction(play.play_id, r.type)}
                                disabled={!!reaction}
                                title={r.label}
                              >
                                {r.emoji}
                              </button>
                            ))}
                          </div>
                          {!isMine && (
                            state.isCzar ? (
                              <button className="btn btn-success w-full" style={{ padding: '9px', fontSize: 13 }} onClick={() => handleCzarPick(play)}>
                                Победитель
                              </button>
                            ) : !voted ? (
                              <button className="btn btn-primary w-full" style={{ padding: '9px', fontSize: 13 }} onClick={() => handleVote(play)}>
                                Голосовать
                              </button>
                            ) : (
                              <div style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-3)', padding: '7px 0' }}>
                                Голос отдан ✓
                              </div>
                            )
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </>
            )}

            {/* RESULTS PHASE */}
            {state.phase === 'results' && state.roundResult && (
              <RoundResults result={state.roundResult} playerId={state.playerId} mode={state.roomConfig?.mode} isCzar={state.isCzar} />
            )}
            {state.phase === 'results' && !state.roundResult && (
              <div className="glass" style={{ padding: 'clamp(24px,6vw,48px)', textAlign: 'center' }}>
                <div className="spinner" style={{ width: 40, height: 40, margin: '0 auto 16px' }} />
                <div style={{ fontWeight: 700, marginBottom: 4 }}>Следующий раунд начинается...</div>
                <div style={{ fontSize: 13, color: 'var(--text-3)' }}>Подождите несколько секунд</div>
              </div>
            )}
          </div>

          {/* SIDEBAR */}
          <div className="game-sidebar">
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 10 }}>
                Игроки
              </div>
              <PlayerList
                players={state.players}
                currentPlayerId={state.playerId}
                czarId={state.czarId}
                playedIds={state.phase === 'playing' ? state.playedIds : undefined}
              />
            </div>

            {state.phase === 'playing' && !state.isCzar && (
              <div className="glass" style={{ padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ width: 36, height: 36, borderRadius: 10, background: 'var(--purple-dim)', border: '1.5px solid var(--glass-border)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 800, color: 'var(--purple-light)', flexShrink: 0 }}>
                  {state.myCards.length}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-3)' }}>карт в руке</div>
              </div>
            )}
          </div>
        </div>
      </div>

      <Toast toasts={toasts} />
    </div>
  )
}

function RoundResults({ result, playerId, mode, isCzar }) {
  const sorted = [...result.plays].sort((a, b) => b.vote_count - a.vote_count)
  const ownPlay = sorted.find(p => p.player_id === playerId)
  return (
    <div>
      <div style={{ marginBottom: 18 }}>
        <h3 style={{ fontWeight: 700, fontSize: 17, marginBottom: 4 }}>
          {result.is_tie ? 'Ничья!' : 'Результаты раунда'}
        </h3>
        <p style={{ fontSize: 13, color: 'var(--text-3)' }}>
          {result.is_tie
            ? 'Никто не получает штраф'
            : mode === 'arena'
            ? 'Голоса засчитаны'
            : 'Победитель скинул карту · Проигравший получил штрафные'}
        </p>
      </div>
      {isCzar && (
        <div style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: 10, padding: '10px 14px', marginBottom: 16, fontSize: 13, color: 'var(--yellow-light)', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontWeight: 700 }}>Ведущий</span>
          <span style={{ color: 'var(--text-3)' }}>— в этом раунде вы не играли карту</span>
        </div>
      )}
      {!isCzar && !ownPlay && (
        <div style={{ background: 'rgba(139,92,246,0.08)', border: '1px solid rgba(139,92,246,0.2)', borderRadius: 10, padding: '10px 14px', marginBottom: 16, fontSize: 13, color: 'var(--text-3)' }}>
          Ваша карта не была сыграна в этом раунде
        </div>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {sorted.map((play, i) => {
          const isWinner = !result.is_tie && result.winners?.includes(play.player_id)
          const isLoser  = !result.is_tie && result.losers?.includes(play.player_id)
          const isMe     = play.player_id === playerId
          return (
            <div key={play.play_id} className={`result-card ${isWinner ? 'winner' : isLoser ? 'loser' : ''}`}
              style={{ display: 'flex', gap: 14, alignItems: 'center', padding: 14, outline: isMe ? '1.5px solid var(--purple)' : 'none' }}>
              <div style={{
                fontSize: 18, fontWeight: 800, width: 32, textAlign: 'center', fontFamily: "'Space Grotesk',sans-serif", flexShrink: 0,
                color: i === 0 ? 'var(--yellow-light)' : i === 1 ? 'var(--text-2)' : 'var(--text-3)',
              }}>
                #{i + 1}
              </div>
              <img
                src={play.meme_url} alt={play.meme_name}
                referrerPolicy="no-referrer"
                style={{ width: 64, height: 64, objectFit: 'cover', borderRadius: 9, flexShrink: 0 }}
              />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 700, fontSize: 14 }}>
                  {play.nickname}{isMe ? <span style={{ fontSize: 11, color: 'var(--purple-light)', marginLeft: 6 }}>ВЫ</span> : null}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {play.meme_name}
                </div>
                <div style={{ display: 'flex', gap: 5, marginTop: 7, flexWrap: 'wrap' }}>
                  {Object.entries(play.reactions || {}).map(([type, cnt]) => (
                    <span key={type} style={{ fontSize: 12, background: 'var(--glass)', padding: '2px 7px', borderRadius: 12, border: '1px solid var(--glass-border)' }}>
                      {type === 'laugh' ? '😂' : type === 'fire' ? '🔥' : '🗑'} {cnt}
                    </span>
                  ))}
                </div>
              </div>
              <div style={{ textAlign: 'right', flexShrink: 0 }}>
                <div style={{ fontSize: 24, fontWeight: 800, fontFamily: "'Space Grotesk',sans-serif", color: isWinner ? 'var(--green-light)' : isLoser ? 'var(--red-light)' : 'var(--text)' }}>
                  {play.vote_count}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-3)' }}>голос{play.vote_count === 1 ? '' : 'а'}</div>
                {isWinner && <div style={{ fontSize: 11, color: 'var(--green-light)', fontWeight: 700, marginTop: 2 }}>Победа</div>}
                {isLoser  && <div style={{ fontSize: 11, color: 'var(--red-light)',   fontWeight: 700, marginTop: 2 }}>Штраф</div>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function GameOverScreen({ gameOver, playerId, onExit }) {
  const isWinner = gameOver?.winner_id === playerId
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 24, position: 'relative', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', top: '30%', left: '50%', transform: 'translate(-50%,-50%)', width: 500, height: 500, borderRadius: '50%', background: isWinner ? 'radial-gradient(circle, rgba(16,185,129,0.1) 0%, transparent 70%)' : 'radial-gradient(circle, rgba(139,92,246,0.08) 0%, transparent 70%)', pointerEvents: 'none' }} />

      <div style={{ textAlign: 'center', marginBottom: 36 }}>
        <div style={{ fontSize: 'clamp(60px, 15vw, 80px)', marginBottom: 14, animation: 'popIn 0.5s cubic-bezier(0.34,1.56,0.64,1)', lineHeight: 1 }}>
          {isWinner ? '🏆' : '🎮'}
        </div>
        <h1 style={{ fontSize: 'clamp(32px, 8vw, 48px)', fontWeight: 900, marginBottom: 12, fontFamily: "'Space Grotesk',sans-serif" }}>
          {isWinner ? (
            <span className="gradient-text">Вы победили!</span>
          ) : (
            <>{gameOver?.winner_nickname} <span style={{ color: 'var(--yellow-light)' }}>победил!</span></>
          )}
        </h1>
        <p style={{ fontSize: 16, color: 'var(--text-2)' }}>
          {isWinner ? 'Поздравляем — первым избавились от всех карт!' : 'Хорошая попытка! Попробуй ещё раз'}
        </p>
      </div>

      <div style={{ width: '100%', maxWidth: 480, marginBottom: 28 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.1em', textAlign: 'center', marginBottom: 14 }}>
          Итоговая таблица
        </div>
        <div className="glass" style={{ borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
          {(gameOver?.leaderboard || []).map((entry, i) => (
            <div key={entry.player_id} style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: '12px 18px',
              borderBottom: i < gameOver.leaderboard.length - 1 ? '1px solid var(--glass-border)' : 'none',
              background: entry.player_id === playerId ? 'var(--purple-dim)' : 'transparent',
            }}>
              <div style={{
                width: 30, height: 30, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontWeight: 800, fontFamily: "'Space Grotesk',sans-serif",
                background: i === 0 ? 'linear-gradient(135deg,var(--yellow),#f97316)' : i === 1 ? 'rgba(148,163,184,0.2)' : i === 2 ? 'rgba(180,83,9,0.2)' : 'var(--glass)',
                color: i === 0 ? '#000' : i <= 2 ? 'var(--text)' : 'var(--text-3)',
                fontSize: 13, flexShrink: 0,
              }}>
                {i === 0 ? '1' : i === 1 ? '2' : i === 2 ? '3' : `#${i + 1}`}
              </div>
              <div style={{ flex: 1, fontWeight: 600, fontSize: 14 }}>
                {entry.nickname}
                {entry.player_id === playerId && <span style={{ fontSize: 11, color: 'var(--purple-light)', marginLeft: 8 }}>ВЫ</span>}
              </div>
              <div style={{ fontSize: 13, fontWeight: 700, color: entry.cards_left === 0 ? 'var(--green-light)' : 'var(--text-2)' }}>
                {entry.cards_left} карт
              </div>
            </div>
          ))}
        </div>
      </div>

      <button className="btn btn-primary btn-lg" onClick={onExit}>В главное меню</button>
    </div>
  )
}
