import api from './client'

export const getMyStats = () => api.get('/stats/me')

export const getLeaderboard = (period = 'all') =>
  api.get('/stats/leaderboard', { params: { period } })
