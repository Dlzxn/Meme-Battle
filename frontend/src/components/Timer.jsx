import React from 'react'

export default function Timer({ seconds, total, label }) {
  const pct = total > 0 ? (seconds / total) * 100 : 0
  const urgent = seconds <= 10

  return (
    <div className="timer-widget" style={{ minWidth: 100 }}>
      {label && <div className="timer-label">{label}</div>}
      <div className={`timer-number ${urgent ? 'urgent' : ''}`}>
        {String(Math.floor(seconds / 60)).padStart(2,'0')}:{String(seconds % 60).padStart(2,'0')}
      </div>
      <div className="timer-bar" style={{ width: 100 }}>
        <div className={`timer-bar-fill ${urgent ? 'urgent' : ''}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
