import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { login } from '../api/auth'
import { useAuth } from '../context/AuthContext'
import { getMe } from '../api/auth'
import Navbar from '../components/Navbar'
import Toast from '../components/Toast'
import useToast from '../hooks/useToast'

export default function LoginPage() {
  const { saveToken, setUser } = useAuth()
  const navigate = useNavigate()
  const { toasts, addToast } = useToast()
  const [form, setForm] = useState({ username: '', password: '' })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const r = await login(form.username, form.password)
      saveToken(r.data.access_token)
      const me = await getMe()
      setUser(me.data)
      navigate('/')
    } catch (err) {
      addToast(err.response?.data?.detail || 'Неверный логин или пароль', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <Navbar />
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <div className="card" style={{ width: '100%', maxWidth: 400 }}>
          <h2 style={{ fontWeight: 800, fontSize: 24, marginBottom: 24 }}>Войти</h2>
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label>Имя пользователя</label>
              <input
                className="input"
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                required
                autoFocus
              />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label>Пароль</label>
              <input
                className="input"
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                required
              />
            </div>
            <button className="btn btn-primary w-full" type="submit" disabled={loading}>
              {loading ? 'Входим...' : 'Войти'}
            </button>
          </form>
          <p style={{ marginTop: 16, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>
            Нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
          </p>
        </div>
      </div>
      <Toast toasts={toasts} />
    </div>
  )
}
