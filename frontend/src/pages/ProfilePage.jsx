import React, { useEffect, useState } from 'react'
import Navbar from '../components/Navbar'
import { useAuth } from '../context/AuthContext'
import { getMyStats } from '../api/stats'

const PACKS = [
  { key:'classic_internet', label:'Классика интернета', icon:'🌐', threshold:10,  color:'var(--cyan)' },
  { key:'russian_segment',  label:'Русский сегмент',    icon:'🇷🇺', threshold:25,  color:'var(--purple)' },
  { key:'gaming',           label:'Гейминг',             icon:'🎮', threshold:50,  color:'var(--green)' },
]

export default function ProfilePage() {
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getMyStats().then(r => setStats(r.data)).finally(() => setLoading(false))
  }, [])

  const wr = stats?.win_rate ?? 0

  return (
    <div className="page">
      <Navbar />
      <div className="container" style={{ paddingTop:48, paddingBottom:60 }}>

        {/* Profile hero */}
        <div style={{ display:'flex', alignItems:'center', gap:24, marginBottom:40 }}>
          <div style={{
            width:80, height:80, borderRadius:22,
            background:'linear-gradient(135deg,var(--purple),var(--pink))',
            display:'flex', alignItems:'center', justifyContent:'center',
            fontSize:36, fontWeight:900, fontFamily:"'Space Grotesk',sans-serif",
            boxShadow:'0 0 40px var(--purple-glow)',
          }}>
            {user?.username[0].toUpperCase()}
          </div>
          <div>
            <h1 style={{ fontSize:32, fontWeight:800 }}>{user?.username}</h1>
            <div style={{ fontSize:14, color:'var(--text-3)', marginTop:4 }}>
              С нами с {user?.created_at ? new Date(user.created_at).toLocaleDateString('ru',{month:'long',year:'numeric'}) : '...'}
            </div>
            <div style={{ display:'flex', gap:8, marginTop:10 }}>
              <span style={{ background:'var(--purple-dim)', border:'1px solid rgba(139,92,246,0.3)', borderRadius:20, padding:'3px 12px', fontSize:12, fontWeight:700, color:'var(--purple-light)' }}>
                🎮 Игрок
              </span>
              {stats?.games_played >= 10 && (
                <span style={{ background:'rgba(245,158,11,0.1)', border:'1px solid rgba(245,158,11,0.3)', borderRadius:20, padding:'3px 12px', fontSize:12, fontWeight:700, color:'var(--yellow-light)' }}>
                  ⭐ Ветеран
                </span>
              )}
            </div>
          </div>
        </div>

        {loading ? (
          <div style={{ display:'flex', justifyContent:'center', padding:60 }}><div className="spinner" /></div>
        ) : (
          <>
            {/* Stats grid */}
            <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:16, marginBottom:28 }}>
              <StatCard icon="🃏" label="Игр сыграно" value={stats?.games_played ?? 0} color="var(--purple)" />
              <StatCard icon="🏆" label="Побед"        value={stats?.games_won ?? 0}    color="var(--yellow)" />
              <StatCard
                icon="📈" label="Винрейт"
                value={`${wr}%`}
                color={wr >= 60 ? 'var(--green)' : wr >= 40 ? 'var(--cyan)' : 'var(--red)'}
                sub={wr >= 60 ? '🔥 Крутой результат!' : wr >= 40 ? '💪 Хороший результат' : '📈 Есть куда расти'}
              />
            </div>

            {/* Win rate bar */}
            <div className="glass" style={{ padding:24, marginBottom:24, borderRadius:'var(--radius)' }}>
              <div style={{ display:'flex', justifyContent:'space-between', marginBottom:10 }}>
                <span style={{ fontWeight:700 }}>Прогресс побед</span>
                <span style={{ color:'var(--text-3)', fontSize:14 }}>{stats?.games_won}/{stats?.games_played} игр</span>
              </div>
              <div style={{ height:8, background:'rgba(255,255,255,0.06)', borderRadius:4, overflow:'hidden' }}>
                <div style={{
                  height:'100%', borderRadius:4, transition:'width 1s cubic-bezier(0.34,1.56,0.64,1)',
                  width:`${wr}%`,
                  background: wr >= 60 ? 'linear-gradient(90deg,var(--green),var(--cyan))' :
                               wr >= 40 ? 'linear-gradient(90deg,var(--purple),var(--cyan))' :
                                          'linear-gradient(90deg,var(--red),var(--purple))',
                }} />
              </div>
            </div>

            {/* Packs */}
            <div className="glass" style={{ padding:24, marginBottom:24, borderRadius:'var(--radius)' }}>
              <h3 style={{ fontWeight:700, fontSize:18, marginBottom:20 }}>🎴 Паки мемов</h3>
              <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit,minmax(200px,1fr))', gap:14 }}>
                {PACKS.map(pack => {
                  const unlocked = stats?.unlocked_packs?.includes(pack.key)
                  const progress = Math.min((stats?.games_played ?? 0) / pack.threshold * 100, 100)
                  return (
                    <div key={pack.key} style={{
                      padding:20, borderRadius:'var(--radius)',
                      background: unlocked ? `${pack.color}10` : 'rgba(255,255,255,0.02)',
                      border: `1.5px solid ${unlocked ? `${pack.color}40` : 'var(--glass-border)'}`,
                      opacity: unlocked ? 1 : 0.7, transition:'all 0.2s',
                    }}>
                      <div style={{ fontSize:32, marginBottom:10 }}>{pack.icon}</div>
                      <div style={{ fontWeight:700, marginBottom:4 }}>{pack.label}</div>
                      <div style={{ fontSize:12, color:'var(--text-3)', marginBottom:12 }}>
                        {unlocked ? '✅ Разблокировано!' : `🔒 Нужно ${pack.threshold} игр`}
                      </div>
                      {!unlocked && (
                        <div>
                          <div style={{ display:'flex', justifyContent:'space-between', fontSize:11, color:'var(--text-3)', marginBottom:6 }}>
                            <span>{stats?.games_played ?? 0}/{pack.threshold}</span>
                            <span>{Math.round(progress)}%</span>
                          </div>
                          <div style={{ height:4, background:'rgba(255,255,255,0.06)', borderRadius:2, overflow:'hidden' }}>
                            <div style={{ height:'100%', width:`${progress}%`, background:`${pack.color}`, borderRadius:2, transition:'width 1s' }} />
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Favorite meme */}
            {stats?.favorite_meme && (
              <div className="glass" style={{ padding:24, borderRadius:'var(--radius)' }}>
                <h3 style={{ fontWeight:700, fontSize:18, marginBottom:20 }}>❤️ Любимый мем</h3>
                <div style={{ display:'flex', gap:20, alignItems:'center' }}>
                  <img src={stats.favorite_meme.url} alt={stats.favorite_meme.name}
                    style={{ width:120, height:120, objectFit:'cover', borderRadius:12, border:'1.5px solid var(--glass-border)' }} />
                  <div>
                    <div style={{ fontSize:22, fontWeight:800, fontFamily:"'Space Grotesk',sans-serif" }}>
                      {stats.favorite_meme.name}
                    </div>
                    <div style={{ color:'var(--text-3)', fontSize:14, marginTop:6 }}>
                      Чаще всего выбираешь этот мем
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function StatCard({ icon, label, value, color, sub }) {
  return (
    <div className="stat-card">
      <div className="stat-card-icon">{icon}</div>
      <div className="stat-card-value" style={{ color }}>{value}</div>
      <div className="stat-card-label">{label}</div>
      {sub && <div style={{ fontSize:11, color:'var(--text-3)', marginTop:6 }}>{sub}</div>}
    </div>
  )
}
