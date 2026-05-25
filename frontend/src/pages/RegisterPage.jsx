import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { register } from '../api/auth'
import { getMe } from '../api/auth'
import { useAuth } from '../context/AuthContext'
import Navbar from '../components/Navbar'
import Toast from '../components/Toast'
import useToast from '../hooks/useToast'

export default function RegisterPage() {
  const { saveToken, setUser } = useAuth()
  const navigate = useNavigate()
  const { toasts, addToast } = useToast()
  const [form, setForm] = useState({ username: '', password: '', confirm: '' })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (form.password !== form.confirm) {
      addToast('Пароли не совпадают', 'error')
      return
    }
    setLoading(true)
    try {
      const r = await register(form.username, form.password)
      saveToken(r.data.access_token)
      const me = await getMe()
      setUser(me.data)
      navigate('/')
    } catch (err) {
      addToast(err.response?.data?.detail || 'Ошибка регистрации', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <Navbar />
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <div className="card" style={{ width: '100%', maxWidth: 400 }}>
          <h2 style={{ fontWeight: 800, fontSize: 24, marginBottom: 24 }}>Регистрация</h2>
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label>Имя пользователя</label>
              <input
                className="input"
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                required
                autoFocus
                minLength={2}
                maxLength={50}
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
                minLength={6}
              />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label>Повторите пароль</label>
              <input
                className="input"
                type="password"
                value={form.confirm}
                onChange={(e) => setForm({ ...form, confirm: e.target.value })}
                required
              />
            </div>
            <button className="btn btn-primary w-full" type="submit" disabled={loading}>
              {loading ? 'Регистрируем...' : 'Зарегистрироваться'}
            </button>
          </form>
          <p style={{ marginTop: 16, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>
            Уже есть аккаунт? <Link to="/login">Войти</Link>
          </p>
        </div>
      </div>
      <Toast toasts={toasts} />
    </div>
  )
}
