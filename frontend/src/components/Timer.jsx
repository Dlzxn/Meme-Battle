import React, { useState, useEffect, useRef } from 'react'

export default function Timer({ seconds, total }) {
  const [display, setDisplay] = useState(seconds)
  const intervalRef = useRef(null)

  // Restart local countdown on new phase (total resets)
  useEffect(() => {
    clearInterval(intervalRef.current)
    setDisplay(seconds)
    if (seconds <= 0) return
    intervalRef.current = setInterval(() => {
      setDisplay(prev => Math.max(0, prev - 1))
    }, 1000)
    return () => clearInterval(intervalRef.current)
  }, [total]) // eslint-disable-line react-hooks/exhaustive-deps

  // Server sync: clamp display to server value (never let local run behind server)
  useEffect(() => {
    setDisplay(prev => Math.min(prev, seconds))
  }, [seconds])

  const pct = total > 0 ? (display / total) * 100 : 0
  const urgent = display <= 10

  return (
    <div className="timer-widget" style={{ minWidth: 100 }}>
      <div className={`timer-number ${urgent ? 'urgent' : ''}`}>
        {String(Math.floor(display / 60)).padStart(2, '0')}:{String(display % 60).padStart(2, '0')}
      </div>
      <div className="timer-bar" style={{ width: 100 }}>
        <div className={`timer-bar-fill ${urgent ? 'urgent' : ''}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
