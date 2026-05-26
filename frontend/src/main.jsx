import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './context/AuthContext'
import { GameProvider } from './context/GameContext'
import { ThemeProvider } from './context/ThemeContext'
import './styles/global.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <GameProvider>
            <div className="bg-orbs" aria-hidden="true">
              <span className="orb orb-1" />
              <span className="orb orb-2" />
              <span className="orb orb-3" />
              <span className="orb orb-4" />
              <span className="orb orb-5" />
            </div>
            <App />
          </GameProvider>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>
)
