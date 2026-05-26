import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'

export default function Navbar() {
  const { user, logout } = useAuth()
  const { theme, toggle } = useTheme()
  const navigate = useNavigate()

  return (
    <nav className="navbar">
      <Link to="/" className="navbar-logo" style={{ textDecoration: 'none' }}>
        <div className="navbar-logo-icon">🃏</div>
        Meme Battle
      </Link>

      <div className="navbar-links">
        <Link to="/leaderboard" className="btn btn-ghost btn-sm">🏆 Рейтинг</Link>
        <button
          className="theme-toggle"
          onClick={toggle}
          title={theme === 'dark' ? 'Светлая тема' : 'Тёмная тема'}
          aria-label="Переключить тему"
        >
          {theme === 'dark' ? '🌙' : '☀️'}
        </button>
        {user ? (
          <>
            <Link to="/profile" className="btn btn-ghost btn-sm">
              <span style={{
                width: 24, height: 24, borderRadius: 7,
                background: 'linear-gradient(135deg, var(--purple), var(--pink))',
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 11, fontWeight: 800,
              }}>
                {user.username[0].toUpperCase()}
              </span>
              {user.username}
            </Link>
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => { logout(); navigate('/') }}
            >
              Выйти
            </button>
          </>
        ) : (
          <>
            <Link to="/login" className="btn btn-ghost btn-sm">Войти</Link>
            <Link to="/register" className="btn btn-primary btn-sm">Регистрация</Link>
          </>
        )}
      </div>
    </nav>
  )
}
