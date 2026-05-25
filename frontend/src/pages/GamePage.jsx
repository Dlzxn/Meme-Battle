import React, { useEffect, useState, useRef } from 'react'
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
  { type: 'laugh', emoji: '😂', label: 'ЛОЛ' },
  { type: 'fire',  emoji: '🔥', label: 'ОГОнь' },
  { type: 'trash', emoji: '🗑️', label: 'Мусор' },
]

export default function GamePage() {
  const { code } = useParams()
  const navigate = useNavigate()
  const { state, setRoom, playCardLocal, dispatch } = useGame()
  const { toasts, addToast } = useToast()
  const [selectedCard, setSelectedCard] = useState(null)
  const [myReactions, setMyReactions] = useState({})
  const timerTotal = useRef(60)

  useEffect(() => {
    if (!state.roomCode) {
      const sc = sessionStorage.getItem('roomCode')
      const si = sessionStorage.getItem('playerId')
      if (sc === code && si) setRoom(code, parseInt(si))
    }
  }, [code, state.roomCode, setRoom])

  const { send } = useGameSocket(state.roomCode || code, state.playerId)

  useEffect(() => {
    if (state.phase === 'playing') timerTotal.current = state.timer || 60
    if (state.phase === 'voting')  timerTotal.current = state.timer || 30
  }, [state.phase])

  const alreadyPlayed = state.playedIds.has(state.playerId)

  const handlePlayCard = () => {
    if (!selectedCard || alreadyPlayed) return
    send('play_card', { card_id: selectedCard })
    playCardLocal(selectedCard)
    setSelectedCard(null)
    addToast('✅ Карта сыграна!', 'success')
  }

  const handleVote = (play) => {
    if (play.player_id === state.playerId || state.votedThisRound) return
    send('vote', { target_player_id: play.player_id, play_id: play.play_id })
    dispatch({ type: 'VOTE_CAST', voter_id: state.playerId })
    addToast('🗳️ Голос отдан!', 'success')
  }

  const handleReaction = (playId, type) => {
    if (myReactions[playId]) return
    send('add_reaction', { play_id: playId, reaction_type: type })
    setMyReactions(p => ({ ...p, [playId]: type }))
  }

  const handleCzarPick = (play) => {
    send('czar_pick', { winner_player_id: play.player_id })
    addToast('👑 Победитель выбран!', 'success')
  }

  if (state.phase === 'game_over') {
    return <GameOverScreen gameOver={state.gameOver} playerId={state.playerId} onExit={() => navigate('/')} />
  }

  if (!state.situation && state.phase !== 'results') {
    return (
      <div className="page">
        <Navbar />
        <div style={{ flex:1, display:'flex', alignItems:'center', justifyContent:'center', flexDirection:'column', gap:16 }}>
          <div className="spinner" style={{ width:48, height:48 }} />
          <div style={{ color: 'var(--text-3)' }}>Загружаем раунд...</div>
        </div>
      </div>
    )
  }

  const phaseInfo = {
    playing: { label: 'Ход', cls: 'play',   icon: '🃏' },
    voting:  { label: 'Голосование', cls: 'vote', icon: '🗳️' },
    results: { label: 'Результаты', cls: 'result', icon: '📊' },
  }[state.phase] || { label: '...', cls: 'play', icon: '⏳' }

  return (
    <div className="page" style={{ background: 'var(--bg)' }}>
      <Navbar />

      {/* TOP BAR */}
      <div style={{
        background: 'rgba(7,7,15,0.9)',
        borderBottom: '1px solid var(--glass-border)',
        backdropFilter: 'blur(20px)',
        padding: '12px 24px',
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        flexWrap: 'wrap',
      }}>
        <div style={{ display:'flex', alignItems:'center', gap:10 }}>
          <span className={`phase-banner ${phaseInfo.cls}`}>
            {phaseInfo.icon} {phaseInfo.label}
          </span>
          <span style={{ fontSize:13, color:'var(--text-3)' }}>Раунд {state.roundNumber}</span>
        </div>
        <div style={{ flex: 1 }} />
        {state.isCzar && (
          <div style={{ display:'inline-flex', alignItems:'center', gap:6, background:'rgba(245,158,11,0.12)', border:'1px solid rgba(245,158,11,0.25)', borderRadius:20, padding:'4px 14px', fontSize:12, fontWeight:700, color:'var(--yellow-light)' }}>
            👑 Вы — Ведущий
          </div>
        )}
        <Timer seconds={state.timer} total={timerTotal.current} />
      </div>

      <div className="container" style={{ paddingTop: 28, paddingBottom: 40, flex: 1 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 260px', gap: 28 }}>

          {/* MAIN */}
          <div style={{ minWidth: 0 }}>

            {/* SITUATION */}
            {state.situation && (
              <div className="situation-card" style={{ marginBottom: 28 }}>
                <div className="situation-card-label">🎲 Ситуация</div>
                <div className="situation-card-text">{state.situation}</div>
              </div>
            )}

            {/* PLAY PHASE */}
            {state.phase === 'playing' && (
              <>
                {state.isCzar ? (
                  <div className="glass" style={{ padding: 48, textAlign: 'center' }}>
                    <div style={{ fontSize: 56, marginBottom: 16 }}>👑</div>
                    <h3 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Вы ведущий этого раунда</h3>
                    <p style={{ color: 'var(--text-2)' }}>Ожидайте ответы игроков — затем выберете победителя</p>
                  </div>
                ) : alreadyPlayed ? (
                  <div className="glass" style={{ padding: 48, textAlign: 'center' }}>
                    <div style={{ fontSize: 56, marginBottom: 16 }}>✅</div>
                    <h3 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Карта сыграна!</h3>
                    <p style={{ color: 'var(--text-2)' }}>Ждём остальных игроков...</p>
                    <div style={{ display:'flex', justifyContent:'center', gap:8, marginTop:20 }}>
                      {state.players.filter(p => p.is_connected).map(p => (
                        <div key={p.id} style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:4 }}>
                          <div style={{
                            width: 36, height: 36, borderRadius: 10, display:'flex', alignItems:'center', justifyContent:'center',
                            background: state.playedIds.has(p.id) ? 'linear-gradient(135deg,var(--green),#059669)' : 'var(--glass)',
                            border: `1.5px solid ${state.playedIds.has(p.id) ? 'var(--green)' : 'var(--glass-border)'}`,
                            fontSize: 14, fontWeight: 800, transition: 'all 0.3s',
                            boxShadow: state.playedIds.has(p.id) ? '0 0 14px var(--green-glow)' : 'none',
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
                    <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:16 }}>
                      <div>
                        <h3 style={{ fontWeight:700, fontSize:18 }}>Твоя рука</h3>
                        <p style={{ fontSize:13, color:'var(--text-3)', marginTop:2 }}>
                          {state.myCards.length} карт{state.myCards.length === 1 ? 'а' : ''} · {selectedCard ? 'Нажми «Сыграть»' : 'Выбери мем для ответа'}
                        </p>
                      </div>
                      <button
                        className="btn btn-primary"
                        onClick={handlePlayCard}
                        disabled={!selectedCard}
                        style={{ padding: '12px 28px' }}
                      >
                        🎴 Сыграть карту
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
                      <div className="glass" style={{ padding:32, textAlign:'center', color:'var(--text-3)' }}>
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
                <div style={{ marginBottom: 20 }}>
                  <h3 style={{ fontWeight:700, fontSize:18 }}>
                    {state.isCzar ? '👑 Выберите лучший мем' : '🗳️ Голосуйте за лучший мем'}
                  </h3>
                  <p style={{ fontSize:13, color:'var(--text-3)', marginTop:4 }}>
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
                        <div style={{ position:'relative', overflow:'hidden' }}>
                          <img src={play.meme_url} alt={play.meme_name}
                            style={{ width:'100%', aspectRatio:'1', objectFit:'cover', display:'block' }} />
                          {play.second_meme_url && (
                            <img src={play.second_meme_url} alt="Second"
                              style={{ width:'100%', aspectRatio:'1', objectFit:'cover', display:'block', borderTop:'2px solid var(--glass-border)' }} />
                          )}
                          {isMine && (
                            <div style={{
                              position:'absolute', inset:0, background:'rgba(0,0,0,0.5)',
                              display:'flex', alignItems:'center', justifyContent:'center', backdropFilter:'blur(2px)',
                            }}>
                              <span style={{ fontSize:13, fontWeight:700, color:'var(--text-2)', background:'rgba(0,0,0,0.6)', padding:'6px 14px', borderRadius:8 }}>
                                Ваш мем
                              </span>
                            </div>
                          )}
                        </div>
                        <div style={{ padding: 14 }}>
                          <div style={{ fontSize:12, color:'var(--text-3)', marginBottom:10, fontWeight:600 }}>
                            {play.meme_name}
                          </div>
                          {/* Reactions */}
                          <div style={{ display:'flex', gap:6, marginBottom:12 }}>
                            {REACTIONS.map(r => (
                              <button key={r.type}
                                className={`reaction-btn ${reaction === r.type ? 'active' : ''}`}
                                onClick={() => handleReaction(play.play_id, r.type)}
                                disabled={!!reaction}
                              >
                                {r.emoji}
                              </button>
                            ))}
                          </div>
                          {/* Vote / Czar button */}
                          {!isMine && (
                            state.isCzar ? (
                              <button
                                className="btn btn-success w-full"
                                style={{ padding:'10px', fontSize:13 }}
                                onClick={() => handleCzarPick(play)}
                              >
                                👑 Победитель!
                              </button>
                            ) : !voted ? (
                              <button
                                className="btn btn-primary w-full"
                                style={{ padding:'10px', fontSize:13 }}
                                onClick={() => handleVote(play)}
                              >
                                🗳️ Голосовать
                              </button>
                            ) : (
                              <div style={{ textAlign:'center', fontSize:12, color:'var(--text-3)', padding:'8px 0' }}>
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
              <RoundResults result={state.roundResult} playerId={state.playerId} />
            )}
          </div>

          {/* SIDEBAR */}
          <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
            <div>
              <div style={{ fontSize:11, fontWeight:700, color:'var(--text-3)', textTransform:'uppercase', letterSpacing:'0.1em', marginBottom:10 }}>
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
              <div className="glass" style={{ padding:'14px 16px', display:'flex', alignItems:'center', gap:12 }}>
                <div style={{ fontSize:28 }}>🃏</div>
                <div>
                  <div style={{ fontWeight:700, fontSize:20, fontFamily:"'Space Grotesk',sans-serif" }}>
                    {state.myCards.length}
                  </div>
                  <div style={{ fontSize:12, color:'var(--text-3)' }}>карт в руке</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <Toast toasts={toasts} />
    </div>
  )
}

function RoundResults({ result, playerId }) {
  const sorted = [...result.plays].sort((a,b) => b.vote_count - a.vote_count)
  return (
    <div>
      <div style={{ marginBottom:20 }}>
        <h3 style={{ fontWeight:700, fontSize:18, marginBottom:4 }}>
          {result.is_tie ? '🤝 Ничья!' : '📊 Результаты раунда'}
        </h3>
        <p style={{ fontSize:13, color:'var(--text-3)' }}>
          {result.is_tie ? 'Никто не получает штраф' : 'Победитель скинул карту · Проигравший получил штрафные'}
        </p>
      </div>
      <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
        {sorted.map((play, i) => {
          const isWinner = !result.is_tie && result.winners?.includes(play.player_id)
          const isLoser  = !result.is_tie && result.losers?.includes(play.player_id)
          const isMe     = play.player_id === playerId
          return (
            <div key={play.play_id} className={`result-card ${isWinner ? 'winner' : isLoser ? 'loser' : ''}`}
              style={{ display:'flex', gap:16, alignItems:'center', padding:16 }}>
              <div style={{
                fontSize:22, fontWeight:800, width:36, textAlign:'center', fontFamily:"'Space Grotesk',sans-serif",
                color: i===0 ? 'var(--yellow-light)' : i===1 ? 'var(--text-2)' : 'var(--text-3)',
              }}>
                #{i+1}
              </div>
              <img src={play.meme_url} alt={play.meme_name}
                style={{ width:72, height:72, objectFit:'cover', borderRadius:10, flexShrink:0 }} />
              <div style={{ flex:1, minWidth:0 }}>
                <div style={{ fontWeight:700, fontSize:15 }}>
                  {play.nickname}{isMe ? <span style={{ fontSize:11, color:'var(--purple-light)', marginLeft:6 }}>ВЫ</span> : null}
                </div>
                <div style={{ fontSize:12, color:'var(--text-3)', marginTop:2, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                  {play.meme_name}
                </div>
                <div style={{ display:'flex', gap:6, marginTop:8, flexWrap:'wrap' }}>
                  {Object.entries(play.reactions || {}).map(([type, cnt]) => (
                    <span key={type} style={{ fontSize:12, background:'var(--glass)', padding:'2px 8px', borderRadius:12, border:'1px solid var(--glass-border)' }}>
                      {type==='laugh'?'😂':type==='fire'?'🔥':'🗑️'} {cnt}
                    </span>
                  ))}
                </div>
              </div>
              <div style={{ textAlign:'right', flexShrink:0 }}>
                <div style={{
                  fontSize:28, fontWeight:800, fontFamily:"'Space Grotesk',sans-serif",
                  color: isWinner ? 'var(--green-light)' : isLoser ? 'var(--red-light)' : 'var(--text)',
                }}>
                  {play.vote_count}
                </div>
                <div style={{ fontSize:11, color:'var(--text-3)' }}>голос{play.vote_count===1?'':'а'}</div>
                {isWinner && <div style={{ fontSize:11, color:'var(--green-light)', fontWeight:700, marginTop:2 }}>🏆 Победа</div>}
                {isLoser  && <div style={{ fontSize:11, color:'var(--red-light)',   fontWeight:700, marginTop:2 }}>💀 Штраф</div>}
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
    <div style={{ minHeight:'100vh', background:'var(--bg)', display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', padding:24, position:'relative', overflow:'hidden' }}>
      {/* BG glow */}
      <div style={{ position:'absolute', top:'30%', left:'50%', transform:'translate(-50%,-50%)', width:600, height:600, borderRadius:'50%', background: isWinner ? 'radial-gradient(circle, rgba(16,185,129,0.12) 0%, transparent 70%)' : 'radial-gradient(circle, rgba(139,92,246,0.1) 0%, transparent 70%)', pointerEvents:'none' }} />

      <div style={{ textAlign:'center', marginBottom:40 }}>
        <div style={{ fontSize:80, marginBottom:16, animation:'popIn 0.5s cubic-bezier(0.34,1.56,0.64,1)' }}>
          {isWinner ? '🏆' : '🎮'}
        </div>
        <h1 style={{ fontSize:48, fontWeight:900, marginBottom:12, fontFamily:"'Space Grotesk',sans-serif" }}>
          {isWinner ? (
            <span className="gradient-text">Вы победили!</span>
          ) : (
            <>{gameOver?.winner_nickname} <span style={{ color:'var(--yellow-light)' }}>победил!</span></>
          )}
        </h1>
        <p style={{ fontSize:18, color:'var(--text-2)' }}>
          {isWinner ? 'Поздравляем — первым избавились от всех карт! 🎉' : 'Хорошая попытка! Попробуй ещё раз 💪'}
        </p>
      </div>

      {/* Leaderboard */}
      <div style={{ width:'100%', maxWidth:500, marginBottom:32 }}>
        <div style={{ fontSize:12, fontWeight:700, color:'var(--text-3)', textTransform:'uppercase', letterSpacing:'0.1em', textAlign:'center', marginBottom:16 }}>
          Итоговая таблица
        </div>
        <div className="glass" style={{ borderRadius:'var(--radius-lg)', overflow:'hidden' }}>
          {(gameOver?.leaderboard || []).map((entry, i) => (
            <div key={entry.player_id} style={{
              display:'flex', alignItems:'center', gap:14,
              padding:'14px 20px',
              borderBottom: i < gameOver.leaderboard.length-1 ? '1px solid var(--glass-border)' : 'none',
              background: entry.player_id === playerId ? 'var(--purple-dim)' : 'transparent',
            }}>
              <div style={{
                width:32, height:32, borderRadius:8, display:'flex', alignItems:'center', justifyContent:'center',
                fontWeight:800, fontFamily:"'Space Grotesk',sans-serif",
                background: i===0 ? 'linear-gradient(135deg,var(--yellow),#f97316)' : i===1 ? 'rgba(148,163,184,0.2)' : i===2 ? 'rgba(180,83,9,0.2)' : 'var(--glass)',
                color: i===0 ? '#000' : i<=2 ? 'var(--text)' : 'var(--text-3)',
                fontSize: 13,
              }}>
                {i===0?'🥇':i===1?'🥈':i===2?'🥉':`#${i+1}`}
              </div>
              <div style={{ flex:1, fontWeight:600 }}>
                {entry.nickname}
                {entry.player_id === playerId && <span style={{ fontSize:11, color:'var(--purple-light)', marginLeft:8 }}>ВЫ</span>}
              </div>
              <div style={{
                fontSize:14, fontWeight:700,
                color: entry.cards_left===0 ? 'var(--green-light)' : 'var(--text-2)',
              }}>
                🃏 {entry.cards_left}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display:'flex', gap:12 }}>
        <button className="btn btn-primary btn-lg" onClick={onExit}>🏠 В главное меню</button>
      </div>
    </div>
  )
}
