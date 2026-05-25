import React, { useState, useEffect, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Toast from '../components/Toast'
import useToast from '../hooks/useToast'
import { createRoom, joinRoom, getPublicRooms } from '../api/rooms'
import { useAuth } from '../context/AuthContext'
import { useGame } from '../context/GameContext'

const MODES = [
  { value: 'no_czar', label: 'Без ведущего', desc: 'Все голосуют', icon: '🗳️' },
  { value: 'czar',    label: 'С ведущим',    desc: 'Czar выбирает', icon: '👑' },
]
const CATEGORIES = [
  { value: 'all',       label: 'Всё вместе',   icon: '🎲' },
  { value: 'work',      label: 'Работа',        icon: '💼' },
  { value: 'school',    label: 'Школа',         icon: '🎒' },
  { value: 'relations', label: 'Отношения',     icon: '❤️' },
  { value: 'internet',  label: 'Интернет',      icon: '🌐' },
]
const TIMER_PLAY = [15, 30, 45, 60, 75, 90, 105, 120]
const TIMER_VOTE = [15, 30, 45, 60]

// Floating card decorations
const FLOATING_MEMES = [
  { url: 'https://i.imgflip.com/1bij.jpg',    style: { top: '12%', left: '4%',  rotate: '-8deg',  scale: 0.8, delay: '0s'  }},
  { url: 'https://i.imgflip.com/4t0m5.jpg',   style: { top: '20%', right: '3%', rotate: '10deg',  scale: 0.75, delay: '0.5s'}},
  { url: 'https://i.imgflip.com/26jxvz.png',  style: { top: '60%', left: '2%',  rotate: '5deg',   scale: 0.7, delay: '1s'  }},
  { url: 'https://i.imgflip.com/2wifvo.jpg',  style: { top: '65%', right: '2%', rotate: '-12deg', scale: 0.72, delay: '1.5s'}},
  { url: 'https://i.imgflip.com/1ur9b0.jpg',  style: { top: '38%', left: '1%',  rotate: '14deg',  scale: 0.65, delay: '0.8s'}},
]

function FloatingCard({ url, style }) {
  return (
    <div style={{
      position: 'absolute',
      top: style.top, left: style.left, right: style.right,
      width: 110,
      borderRadius: 12,
      overflow: 'hidden',
      border: '1.5px solid rgba(255,255,255,0.08)',
      boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
      transform: `rotate(${style.rotate}) scale(${style.scale})`,
      animation: `floatCard 6s ease-in-out infinite`,
      animationDelay: style.delay,
      opacity: 0.55,
      pointerEvents: 'none',
      zIndex: 0,
    }}>
      <img src={url} alt="" style={{ width: '100%', display: 'block', aspectRatio: '1', objectFit: 'cover' }} />
      <style>{`
        @keyframes floatCard {
          0%,100% { transform: rotate(${style.rotate}) scale(${style.scale}) translateY(0px); }
          50%      { transform: rotate(${style.rotate}) scale(${style.scale}) translateY(-14px); }
        }
      `}</style>
    </div>
  )
}

export default function HomePage() {
  const { user } = useAuth()
  const { setRoom } = useGame()
  const navigate = useNavigate()
  const { toasts, addToast } = useToast()
  const [tab, setTab] = useState('join')
  const [joinCode, setJoinCode] = useState('')
  const [nickname, setNickname] = useState('')
  const [loading, setLoading] = useState(false)
  const [publicRooms, setPublicRooms] = useState([])
  const [form, setForm] = useState({
    mode: 'no_czar', category: 'all',
    timer_play: 60, timer_vote: 30,
    cards_count: 7, penalty_count: 1,
    is_public: false, custom_situations: '',
  })

  useEffect(() => {
    if (tab === 'public') getPublicRooms().then(r => setPublicRooms(r.data)).catch(() => {})
  }, [tab])

  const go = async (fn) => {
    setLoading(true)
    try { await fn() } finally { setLoading(false) }
  }

  const apiErr = (e, fallback) => {
    const detail = e.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map(d => d.msg || JSON.stringify(d)).join('; ')
    return fallback
  }

  const handleJoin = () => go(async () => {
    if (!joinCode.trim()) { addToast('Введите код комнаты', 'error'); return }
    if (!user && !nickname.trim()) { addToast('Введите никнейм', 'error'); return }
    const nick = user ? user.username : nickname.trim()
    const r = await joinRoom(joinCode.trim().toUpperCase(), nick)
    setRoom(r.data.room_code, r.data.player_id)
    navigate(`/lobby/${r.data.room_code}`)
  }).catch(e => addToast(apiErr(e, 'Комната не найдена'), 'error'))

  const handleCreate = () => go(async () => {
    if (!user && !nickname.trim()) { addToast('Введите никнейм', 'error'); return }
    const nick = user ? user.username : nickname.trim()
    const r = await createRoom({ ...form, nickname: nick, custom_situations: form.custom_situations || null })
    setRoom(r.data.room_code, r.data.player_id)
    navigate(`/lobby/${r.data.room_code}`)
  }).catch(e => addToast(apiErr(e, 'Ошибка создания'), 'error'))

  const handleJoinPublic = (code) => go(async () => {
    if (!user && !nickname.trim()) { addToast('Введите никнейм выше', 'error'); return }
    const nick = user ? user.username : nickname.trim()
    const r = await joinRoom(code, nick)
    setRoom(r.data.room_code, r.data.player_id)
    navigate(`/lobby/${r.data.room_code}`)
  }).catch(e => addToast(apiErr(e, 'Ошибка'), 'error'))

  const pf = (k, v) => setForm(f => ({ ...f, [k]: v }))

  return (
    <div className="page" style={{ background: 'var(--bg)' }}>
      <Navbar />

      {/* HERO */}
      <div style={{ position: 'relative', overflow: 'hidden', padding: '80px 0 64px' }}>
        {FLOATING_MEMES.map((m, i) => <FloatingCard key={i} {...m} />)}

        <div style={{ textAlign: 'center', position: 'relative', zIndex: 1 }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            background: 'rgba(139,92,246,0.12)', border: '1px solid rgba(139,92,246,0.25)',
            borderRadius: 20, padding: '6px 16px', marginBottom: 24,
            fontSize: 12, fontWeight: 700, color: 'var(--purple-light)',
            textTransform: 'uppercase', letterSpacing: '0.1em',
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green)', boxShadow: '0 0 8px var(--green)' }} />
            Мультиплеер · До 8 игроков
          </div>

          <h1 style={{ fontSize: 'clamp(48px, 8vw, 80px)', fontWeight: 900, lineHeight: 1.05, marginBottom: 20 }}>
            <span className="gradient-text">Meme Battle</span>
          </h1>

          <p style={{ fontSize: 18, color: 'var(--text-2)', maxWidth: 480, margin: '0 auto 40px', lineHeight: 1.6 }}>
            Отвечай на ситуации мемами из своей колоды.<br />
            Побеждай — и избавляйся от карт первым.
          </p>

          {!user && (
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginBottom: 32 }}>
              <Link to="/register" className="btn btn-primary btn-lg">🚀 Регистрация</Link>
              <Link to="/login" className="btn btn-secondary btn-lg">Войти</Link>
            </div>
          )}
        </div>
      </div>

      {/* MAIN BLOCK */}
      <div className="container" style={{ paddingBottom: 80 }}>
        {!user && (
          <div style={{ maxWidth: 400, margin: '0 auto 32px', textAlign: 'center' }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label>Никнейм для гостя</label>
              <input
                className="input"
                placeholder="Как тебя зовут?"
                value={nickname}
                onChange={e => setNickname(e.target.value)}
                maxLength={30}
                style={{ textAlign: 'center', fontSize: 16 }}
              />
            </div>
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 32 }}>
          <div className="tabs">
            {[
              { key: 'join',   label: '🔑 По коду'  },
              { key: 'create', label: '✨ Создать'   },
              { key: 'public', label: '🌍 Публичные' },
            ].map(t => (
              <button key={t.key} className={`tab-btn ${tab === t.key ? 'active' : ''}`} onClick={() => setTab(t.key)}>
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <div style={{ maxWidth: tab === 'create' ? 680 : 500, margin: '0 auto' }}>

          {/* JOIN TAB */}
          {tab === 'join' && (
            <div className="glass" style={{ padding: 32 }}>
              <h2 style={{ fontWeight: 700, fontSize: 22, marginBottom: 24 }}>Войти в комнату</h2>
              <div style={{ marginBottom: 24 }}>
                <label style={{ display: 'block', fontSize: 11, fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 10 }}>
                  Код комнаты
                </label>
                <input
                  className="input"
                  placeholder="A1B2C3"
                  value={joinCode}
                  onChange={e => setJoinCode(e.target.value.toUpperCase())}
                  maxLength={6}
                  style={{ fontSize: 32, letterSpacing: 12, textAlign: 'center', fontFamily: "'Space Grotesk',sans-serif", fontWeight: 700 }}
                  onKeyDown={e => e.key === 'Enter' && handleJoin()}
                />
              </div>
              <button className="btn btn-primary btn-lg w-full" onClick={handleJoin} disabled={loading}>
                {loading ? <><div className="spinner" style={{ width:18,height:18,borderWidth:2 }} /> Входим...</> : '🎮 Войти в комнату'}
              </button>
            </div>
          )}

          {/* CREATE TAB */}
          {tab === 'create' && (
            <div className="glass" style={{ padding: 32 }}>
              <h2 style={{ fontWeight: 700, fontSize: 22, marginBottom: 24 }}>Создать комнату</h2>

              {/* Mode */}
              <div style={{ marginBottom: 20 }}>
                <label style={{ display:'block', fontSize:11, fontWeight:700, color:'var(--text-3)', textTransform:'uppercase', letterSpacing:'0.1em', marginBottom:10 }}>
                  Режим игры
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  {MODES.map(m => (
                    <button key={m.value} onClick={() => pf('mode', m.value)} style={{
                      padding: '14px 16px', borderRadius: 12, border: '1.5px solid',
                      borderColor: form.mode === m.value ? 'var(--purple)' : 'var(--glass-border)',
                      background: form.mode === m.value ? 'var(--purple-dim)' : 'var(--glass)',
                      cursor: 'pointer', textAlign: 'left', transition: 'all 0.15s',
                    }}>
                      <div style={{ fontSize: 20, marginBottom: 4 }}>{m.icon}</div>
                      <div style={{ fontWeight: 700, fontSize: 14, color: form.mode === m.value ? 'var(--purple-light)' : 'var(--text)' }}>{m.label}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-3)' }}>{m.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Category */}
              <div style={{ marginBottom: 20 }}>
                <label style={{ display:'block', fontSize:11, fontWeight:700, color:'var(--text-3)', textTransform:'uppercase', letterSpacing:'0.1em', marginBottom:10 }}>
                  Категория ситуаций
                </label>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {CATEGORIES.map(c => (
                    <button key={c.value} onClick={() => pf('category', c.value)} style={{
                      padding: '8px 14px', borderRadius: 20, border: '1.5px solid',
                      borderColor: form.category === c.value ? 'var(--cyan)' : 'var(--glass-border)',
                      background: form.category === c.value ? 'rgba(6,182,212,0.1)' : 'var(--glass)',
                      color: form.category === c.value ? 'var(--cyan-light)' : 'var(--text-2)',
                      cursor: 'pointer', fontSize: 13, fontWeight: 600, transition: 'all 0.15s',
                    }}>
                      {c.icon} {c.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Sliders row */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label>Таймер хода</label>
                  <select className="input" value={form.timer_play} onChange={e => pf('timer_play', +e.target.value)}>
                    {TIMER_PLAY.map(t => <option key={t} value={t}>{t} сек</option>)}
                  </select>
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label>Таймер голосования</label>
                  <select className="input" value={form.timer_vote} onChange={e => pf('timer_vote', +e.target.value)}>
                    {TIMER_VOTE.map(t => <option key={t} value={t}>{t} сек</option>)}
                  </select>
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label>Карт в колоде</label>
                  <select className="input" value={form.cards_count} onChange={e => pf('cards_count', +e.target.value)}>
                    {[5,6,7,8,9,10].map(n => <option key={n} value={n}>{n} карт</option>)}
                  </select>
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label>Штраф за проигрыш</label>
                  <select className="input" value={form.penalty_count} onChange={e => pf('penalty_count', +e.target.value)}>
                    <option value={1}>1 карта</option>
                    <option value={2}>2 карты</option>
                  </select>
                </div>
              </div>

              {/* Privacy */}
              <div style={{ marginBottom: 20 }}>
                <label style={{ display:'block', fontSize:11, fontWeight:700, color:'var(--text-3)', textTransform:'uppercase', letterSpacing:'0.1em', marginBottom:10 }}>
                  Тип комнаты
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  {[
                    { v: false, label: '🔒 Приватная', desc: 'Только по коду' },
                    { v: true,  label: '🌍 Публичная',  desc: 'Любой может войти' },
                  ].map(o => (
                    <button key={String(o.v)} onClick={() => pf('is_public', o.v)} style={{
                      padding: '12px 16px', borderRadius: 12, border: '1.5px solid',
                      borderColor: form.is_public === o.v ? 'var(--purple)' : 'var(--glass-border)',
                      background: form.is_public === o.v ? 'var(--purple-dim)' : 'var(--glass)',
                      cursor: 'pointer', textAlign: 'left', transition: 'all 0.15s',
                    }}>
                      <div style={{ fontWeight: 700, fontSize: 14, color: form.is_public === o.v ? 'var(--purple-light)' : 'var(--text)' }}>{o.label}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-3)' }}>{o.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Custom situations */}
              <div className="form-group" style={{ marginBottom: 24 }}>
                <label>Свои ситуации (по одной на строку, необязательно)</label>
                <textarea
                  className="input"
                  rows={3}
                  placeholder={"Дедлайн через час, ты ещё не начинал\nМенеджер просит «маленькую правку»"}
                  value={form.custom_situations}
                  onChange={e => pf('custom_situations', e.target.value)}
                />
              </div>

              <button className="btn btn-primary btn-lg w-full" onClick={handleCreate} disabled={loading}>
                {loading ? <><div className="spinner" style={{width:18,height:18,borderWidth:2}} /> Создаём...</> : '✨ Создать комнату'}
              </button>
            </div>
          )}

          {/* PUBLIC TAB */}
          {tab === 'public' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {publicRooms.length === 0 && (
                <div className="glass" style={{ padding: 48, textAlign: 'center', color: 'var(--text-3)' }}>
                  <div style={{ fontSize: 48, marginBottom: 12 }}>🌵</div>
                  Нет публичных комнат
                </div>
              )}
              {publicRooms.map(r => (
                <div key={r.id} className="glass" style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 16 }}>
                  <div style={{
                    width: 44, height: 44, borderRadius: 12,
                    background: 'linear-gradient(135deg,var(--purple),var(--pink))',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontWeight: 800, fontSize: 16, fontFamily: "'Space Grotesk',sans-serif",
                    flexShrink: 0,
                  }}>
                    {r.code[0]}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700, fontFamily: "'Space Grotesk',sans-serif", letterSpacing: 2 }}>{r.code}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 2 }}>
                      {r.mode === 'czar' ? '👑 С ведущим' : '🗳️ Голосование'} · {r.player_count}/8 игроков
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ display:'flex', gap:3 }}>
                      {Array.from({length:8}).map((_,i) => (
                        <div key={i} style={{
                          width:6, height:6, borderRadius:'50%',
                          background: i < r.player_count ? 'var(--green)' : 'var(--glass-border)',
                          boxShadow: i < r.player_count ? '0 0 6px var(--green)' : 'none',
                        }} />
                      ))}
                    </div>
                    <button className="btn btn-primary btn-sm" onClick={() => handleJoinPublic(r.code)} disabled={loading}>
                      Войти
                    </button>
                  </div>
                </div>
              ))}
              <button className="btn btn-secondary w-full" onClick={() => getPublicRooms().then(r => setPublicRooms(r.data))}>
                🔄 Обновить
              </button>
            </div>
          )}
        </div>

        {/* FEATURES */}
        <div style={{ marginTop: 80 }}>
          <div style={{ textAlign: 'center', marginBottom: 40 }}>
            <h2 style={{ fontSize: 32, fontWeight: 800 }}>Как играть?</h2>
            <p style={{ color: 'var(--text-2)', marginTop: 8 }}>Три фазы — три шанса победить</p>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 20 }}>
            {[
              { icon: '🃏', color: 'var(--purple)', title: 'Сыграй карту', desc: 'Выбери лучший мем из своей руки для текущей ситуации. Успей до таймера!' },
              { icon: '🗳️', color: 'var(--pink)',   title: 'Проголосуй',   desc: 'Все мемы раскрываются анонимно. Голосуй за лучший — только не за себя.' },
              { icon: '🏆', color: 'var(--cyan)',   title: 'Победи',       desc: 'Победитель раунда избавляется от карты. Первый без карт — выигрывает.' },
            ].map((f, i) => (
              <div key={i} className="glass" style={{ padding: 28, textAlign: 'center' }}>
                <div style={{
                  width: 56, height: 56, borderRadius: 16, margin: '0 auto 16px',
                  background: `${f.color}20`, border: `1.5px solid ${f.color}40`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28,
                }}>
                  {f.icon}
                </div>
                <h3 style={{ fontWeight: 700, fontSize: 18, marginBottom: 8 }}>{f.title}</h3>
                <p style={{ color: 'var(--text-2)', fontSize: 14, lineHeight: 1.6 }}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <Toast toasts={toasts} />
    </div>
  )
}
