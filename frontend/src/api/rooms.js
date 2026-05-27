import api from './client'

export const createRoom = (data) => api.post('/rooms', data)

export const joinRoom = (code, nickname) =>
  api.post(`/rooms/${code}/join`, null, { params: { nickname } })

export const getPublicRooms = () => api.get('/rooms/public')

export const getRoomStatus = (code) => api.get(`/rooms/${code}/status`)

export const kickPlayer = (code, playerId) =>
  api.delete(`/rooms/${code}/kick/${playerId}`)
