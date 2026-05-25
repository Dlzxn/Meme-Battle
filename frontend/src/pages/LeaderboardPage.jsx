import React, { useEffect, useState } from 'react'
import Navbar from '../components/Navbar'
import { getLeaderboard } from '../api/stats'

const PERIODS = [
  { value:'all',   label:'Всё время' },
  { value:'month', label:'Месяц' },
  { value:'week',  label:'Неделя' },
]

const MEDALS = ['🥇','🥈','🥉']

export default function LeaderboardPage() {
  const [period, setPeriod] = useState('all')
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    getLeaderboard(period).then(r => setEntries(r.data)).finally(() => setLoading(false))
  }, [period])

  const top3 = entries.slice(0, 3)
  const rest  = entries.slice(3)

  return (
    <div className="page">
      <Navbar />
      <div className="container" style={{ paddingTop:48, paddingBottom:60 }}>

        <div style={{ textAlign:'center', marginBottom:40 }}>
          <div style={{ fontSize:64, marginBottom:16 }}>🏆</div>
          <h1 style={{ fontSize:40, fontWeight:900 }}>Таблица лидеров</h1>
          <p style={{ color:'var(--text-2)', marginTop:8 }}>Минимум 10 игр для попадания в рейтинг</p>
        </div>

        {/* Period tabs */}
        <div style={{ display:'flex', justifyContent:'center', marginBottom:40 }}>
          <div className="tabs">
            {PERIODS.map(p => (
              <button key={p.value} className={`tab-btn ${period===p.value?'active':''}`} onClick={() => setPeriod(p.value)}>
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div style={{ display:'flex', justifyContent:'center', padding:60 }}><div className="spinner" /></div>
        ) : entries.length === 0 ? (
          <div className="glass" style={{ padding:60, textAlign:'center', borderRadius:'var(--radius-lg)' }}>
            <div style={{ fontSize:48, marginBottom:12 }}>🌵</div>
            <div style={{ color:'var(--text-3)' }}>Пока никого нет в рейтинге</div>
          </div>
        ) : (
          <>
            {/* Top 3 podium */}
            {top3.length >= 2 && (
              <div style={{ display:'flex', justifyContent:'center', alignItems:'flex-end', gap:16, marginBottom:40 }}>
                {[top3[1], top3[0], top3[2]].filter(Boolean).map((entry, podiumIdx) => {
                  const actualIdx = podiumIdx === 0 ? 1 : podiumIdx === 1 ? 0 : 2
                  const heights   = [140, 180, 110]
                  const h         = heights[actualIdx]
                  const colors    = [
                    'linear-gradient(135deg,rgba(148,163,184,0.2),rgba(148,163,184,0.05))',
                    'linear-gradient(135deg,rgba(245,158,11,0.25),rgba(245,158,11,0.05))',
                    'linear-gradient(135deg,rgba(180,83,9,0.2),rgba(180,83,9,0.05))',
                  ]
                  return (
                    <div key={entry.rank} style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:12 }}>
                      <div style={{ fontSize:28 }}>{MEDALS[actualIdx]}</div>
                      <div style={{
                        width:56, height:56, borderRadius:16,
                        background:`linear-gradient(135deg,var(--purple),var(--pink))`,
                        display:'flex', alignItems:'center', justifyContent:'center',
                        fontSize:22, fontWeight:800, fontFamily:"'Space Grotesk',sans-serif",
                        boxShadow: actualIdx===0 ? '0 0 30px var(--yellow-glow)' : 'none',
                      }}>
                        {entry.username[0].toUpperCase()}
                      </div>
                      <div style={{ fontWeight:700, fontSize:14, textAlign:'center', maxWidth:90, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                        {entry.username}
                      </div>
                      <div style={{
                        width:120, height:h, borderRadius:'14px 14px 0 0',
                        background: colors[actualIdx],
                        border:'1.5px solid var(--glass-border)',
                        display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:4,
                      }}>
                        <div style={{ fontSize:22, fontWeight:800, fontFamily:"'Space Grotesk',sans-serif", color: actualIdx===0?'var(--yellow-light)':'var(--text)' }}>
                          {entry.win_rate}%
                        </div>
                        <div style={{ fontSize:11, color:'var(--text-3)' }}>{entry.games_won}В / {entry.games_played}И</div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}

            {/* Rest of table */}
            {rest.length > 0 && (
              <div className="glass" style={{ borderRadius:'var(--radius-lg)', overflow:'hidden' }}>
                <div style={{ padding:'12px 20px', borderBottom:'1px solid var(--glass-border)', display:'grid', gridTemplateColumns:'48px 1fr 80px 80px 100px', gap:12, fontSize:11, fontWeight:700, color:'var(--text-3)', textTransform:'uppercase', letterSpacing:'0.08em' }}>
                  <div>#</div>
                  <div>Игрок</div>
                  <div style={{ textAlign:'center' }}>Игр</div>
                  <div style={{ textAlign:'center' }}>Побед</div>
                  <div style={{ textAlign:'right' }}>Винрейт</div>
                </div>
                {rest.map((entry, i) => (
                  <div key={entry.rank}
                    style={{
                      padding:'14px 20px',
                      display:'grid', gridTemplateColumns:'48px 1fr 80px 80px 100px', gap:12,
                      alignItems:'center',
                      borderBottom: i < rest.length-1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                      transition:'background 0.15s', cursor:'default',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background='rgba(255,255,255,0.03)'}
                    onMouseLeave={e => e.currentTarget.style.background=''}
                  >
                    <div style={{ fontWeight:800, color:'var(--text-3)', fontFamily:"'Space Grotesk',sans-serif" }}>
                      #{entry.rank}
                    </div>
                    <div style={{ display:'flex', alignItems:'center', gap:10 }}>
                      <div style={{
                        width:32, height:32, borderRadius:9,
                        background:'linear-gradient(135deg,var(--purple),var(--pink))',
                        display:'flex', alignItems:'center', justifyContent:'center',
                        fontSize:13, fontWeight:800,
                      }}>
                        {entry.username[0].toUpperCase()}
                      </div>
                      <span style={{ fontWeight:600 }}>{entry.username}</span>
                    </div>
                    <div style={{ textAlign:'center', color:'var(--text-3)', fontSize:14 }}>{entry.games_played}</div>
                    <div style={{ textAlign:'center', color:'var(--text-3)', fontSize:14 }}>{entry.games_won}</div>
                    <div style={{ textAlign:'right' }}>
                      <span style={{
                        fontWeight:800, fontSize:15, fontFamily:"'Space Grotesk',sans-serif",
                        color: entry.win_rate>=60 ? 'var(--green-light)' : entry.win_rate>=40 ? 'var(--cyan-light)' : 'var(--red-light)',
                      }}>
                        {entry.win_rate}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
