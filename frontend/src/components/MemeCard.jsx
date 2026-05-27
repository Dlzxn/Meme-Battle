import React, { useState, useRef, useCallback } from 'react'

const SPECIAL_LABELS = {
  steal:        'КРАЖА',
  skip_penalty: 'ЩИТ',
  double_play:  'ДАБЛ',
}

const FALLBACK = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200"%3E%3Crect width="200" height="200" fill="%231a1a2e"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-size="48" fill="%238b5cf6"%3E%3F%3C/text%3E%3C/svg%3E'

export default function MemeCard({ card, selected, onClick, disabled, size = 'md' }) {
  const minW = size === 'sm' ? 100 : size === 'lg' ? 170 : 120
  const [preview, setPreview] = useState(false)
  const hoverTimer = useRef(null)

  const handleMouseEnter = useCallback(() => {
    hoverTimer.current = setTimeout(() => setPreview(true), 1000)
  }, [])

  const handleMouseLeave = useCallback(() => {
    clearTimeout(hoverTimer.current)
    setPreview(false)
  }, [])

  return (
    <>
      <div
        className={`meme-card ${selected ? 'selected' : ''} ${card.is_special ? 'special' : ''}`}
        onClick={!disabled ? onClick : undefined}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        style={{ opacity: disabled ? 0.45 : 1, cursor: disabled ? 'default' : 'pointer', minWidth: minW }}
      >
        {card.is_special && (
          <div className="meme-card-special-badge">
            {SPECIAL_LABELS[card.special_type] ?? 'СПЕЦ'}
          </div>
        )}
        {selected && (
          <div className="meme-card-select-check">✓</div>
        )}
        <img
          src={card.url}
          alt={card.name}
          loading="lazy"
          referrerPolicy="no-referrer"
          onError={e => { e.currentTarget.src = FALLBACK }}
        />
        <div className="meme-card-footer">{card.name}</div>
      </div>

      {preview && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 10000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(0,0,0,0.8)',
            backdropFilter: 'blur(8px)',
            animation: 'memePreviewIn 0.15s ease both',
          }}
          onClick={() => setPreview(false)}
          onMouseLeave={() => { clearTimeout(hoverTimer.current); setPreview(false) }}
        >
          <style>{`
            @keyframes memePreviewIn {
              from { opacity: 0; transform: scale(0.9); }
              to   { opacity: 1; transform: scale(1); }
            }
          `}</style>
          <div style={{ position: 'relative', maxWidth: '80vw', maxHeight: '80vh' }}>
            <img
              src={card.url}
              alt={card.name}
              referrerPolicy="no-referrer"
              onError={e => { e.currentTarget.src = FALLBACK }}
              style={{
                maxWidth: '80vw',
                maxHeight: '75vh',
                borderRadius: 16,
                boxShadow: '0 24px 80px rgba(0,0,0,0.8)',
                display: 'block',
                objectFit: 'contain',
              }}
            />
            <div style={{
              position: 'absolute',
              bottom: -36,
              left: 0, right: 0,
              textAlign: 'center',
              fontSize: 13,
              fontWeight: 600,
              color: 'rgba(255,255,255,0.65)',
            }}>
              {card.name}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
