import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'

const IconSun = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="5"/>
    <line x1="12" y1="1" x2="12" y2="3"/>
    <line x1="12" y1="21" x2="12" y2="23"/>
    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
    <line x1="1" y1="12" x2="3" y2="12"/>
    <line x1="21" y1="12" x2="23" y2="12"/>
    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
  </svg>
)

const IconMoon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
  </svg>
)

const IconTrophy = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="8 1 4 5 8 9"/>
    <path d="M4 5h16"/>
    <polyline points="16 1 20 5 16 9"/>
    <path d="M12 9v13"/>
    <path d="M8 22h8"/>
  </svg>
)

export default function Navbar() {
  const { user, logout } = useAuth()
  const { theme, toggle } = useTheme()
  const navigate = useNavigate()

  return (
    <nav className="navbar">
      <Link to="/" className="navbar-logo" style={{ textDecoration: 'none' }}>
        <div className="navbar-logo-icon" style={{ fontSize: 13, fontWeight: 900, letterSpacing: '-0.5px' }}>
          MB
        </div>
        <span>Meme Battle</span>
      </Link>

      <div className="navbar-links">
        <Link to="/leaderboard" className="btn btn-ghost btn-sm navbar-hide-mobile" style={{ gap: 6 }}>
          <IconTrophy />
          Рейтинг
        </Link>
        <button
          className="theme-toggle"
          onClick={toggle}
          title={theme === 'dark' ? 'Светлая тема' : 'Тёмная тема'}
          aria-label="Переключить тему"
        >
          {theme === 'dark' ? <IconSun /> : <IconMoon />}
        </button>
        {user ? (
          <>
            <Link to="/profile" className="btn btn-ghost btn-sm" style={{ gap: 6 }}>
              <span style={{
                width: 22, height: 22, borderRadius: 6,
                background: 'linear-gradient(135deg, var(--purple), var(--pink))',
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 10, fontWeight: 800, flexShrink: 0, color: '#fff',
              }}>
                {user.username[0].toUpperCase()}
              </span>
              <span className="navbar-hide-mobile">{user.username}</span>
            </Link>
            <button
              className="btn btn-ghost btn-sm navbar-hide-mobile"
              onClick={() => { logout(); navigate('/') }}
            >
              Выйти
            </button>
          </>
        ) : (
          <>
            <Link to="/login" className="btn btn-ghost btn-sm">Войти</Link>
            <Link to="/register" className="btn btn-primary btn-sm navbar-hide-mobile">Регистрация</Link>
          </>
        )}
      </div>
    </nav>
  )
}
