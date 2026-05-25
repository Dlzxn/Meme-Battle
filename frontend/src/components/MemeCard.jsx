import React from 'react'

const SPECIAL_LABELS = {
  steal:       '🎭 КРАЖА',
  skip_penalty:'🛡 ЩИТ',
  double_play: '✌️ ДАБЛ',
}

export default function MemeCard({ card, selected, onClick, disabled, size = 'md' }) {
  const minW = size === 'sm' ? 110 : size === 'lg' ? 180 : 130

  return (
    <div
      className={`meme-card ${selected ? 'selected' : ''} ${card.is_special ? 'special' : ''}`}
      onClick={!disabled ? onClick : undefined}
      style={{ opacity: disabled ? 0.45 : 1, cursor: disabled ? 'default' : 'pointer', minWidth: minW }}
    >
      {card.is_special && (
        <div className="meme-card-special-badge">
          {SPECIAL_LABELS[card.special_type] ?? '⭐ СПЕЦ'}
        </div>
      )}
      {selected && (
        <div className="meme-card-select-check">✓</div>
      )}
      <img src={card.url} alt={card.name} loading="lazy" />
      <div className="meme-card-footer">{card.name}</div>
    </div>
  )
}
