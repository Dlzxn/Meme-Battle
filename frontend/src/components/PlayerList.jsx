import React from 'react'

const AVATAR_COLORS = [
  'linear-gradient(135deg,#8b5cf6,#ec4899)',
  'linear-gradient(135deg,#06b6d4,#8b5cf6)',
  'linear-gradient(135deg,#f59e0b,#ef4444)',
  'linear-gradient(135deg,#10b981,#06b6d4)',
  'linear-gradient(135deg,#ec4899,#f59e0b)',
  'linear-gradient(135deg,#6366f1,#22d3ee)',
  'linear-gradient(135deg,#14b8a6,#8b5cf6)',
  'linear-gradient(135deg,#f43f5e,#8b5cf6)',
]

export default function PlayerList({ players, currentPlayerId, czarId, playedIds, onKick, isHost }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {players.map((p, i) => {
        const isYou   = p.id === currentPlayerId
        const isCzar  = p.id === czarId
        const played  = playedIds?.has(p.id)
        const cls     = `player-badge ${isYou ? 'is-you' : ''} ${isCzar ? 'is-czar' : ''}`

        return (
          <div key={p.id} className={cls}>
            <div className="player-avatar" style={{ background: AVATAR_COLORS[i % AVATAR_COLORS.length] }}>
              {p.nickname[0].toUpperCase()}
            </div>

            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="player-name" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {p.nickname}
              </div>
              {!p.is_connected && (
                <div style={{ fontSize: 11, color: 'var(--red-light)' }}>отключён</div>
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              {p.is_host && <span className="player-tag host">ХОСТ</span>}
              {isCzar    && <span className="player-tag czar">👑</span>}
              {isYou     && <span className="player-tag you">ВЫ</span>}
              {playedIds && (
                <span className={`player-tag ${played ? 'played' : 'waiting'}`}>
                  {played ? '✓' : '...'}
                </span>
              )}
              {p.card_count !== undefined && !playedIds && (
                <span style={{ fontSize: 12, color: 'var(--text-3)', fontWeight: 600 }}>
                  🃏{p.card_count}
                </span>
              )}
              {isHost && !isYou && onKick && (
                <button className="btn btn-danger btn-sm" style={{ padding: '4px 10px', fontSize: 11 }} onClick={() => onKick(p.id)}>
                  Кик
                </button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
