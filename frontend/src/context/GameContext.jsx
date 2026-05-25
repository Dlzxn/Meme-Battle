import React, { createContext, useContext, useReducer, useCallback } from 'react'

const GameContext = createContext(null)

const initialState = {
  roomCode: null,
  playerId: null,
  players: [],
  isHost: false,
  phase: 'lobby', // lobby | playing | voting | results | game_over
  situation: null,
  myCards: [],
  plays: [],
  roundId: null,
  roundNumber: 1,
  timer: 0,
  timerPhase: null,
  czarId: null,
  isCzar: false,
  roundResult: null,
  gameOver: null,
  playedIds: new Set(),
  votedThisRound: false,
}

function gameReducer(state, action) {
  switch (action.type) {
    case 'SET_ROOM':
      return { ...state, roomCode: action.roomCode, playerId: action.playerId }

    case 'ROOM_UPDATED':
      return {
        ...state,
        players: action.players,
        isHost: action.players.find((p) => p.id === state.playerId)?.is_host ?? state.isHost,
      }

    case 'GAME_STARTED':
      return { ...state, phase: 'playing' }

    case 'SITUATION_DEALT':
      return {
        ...state,
        phase: 'playing',
        situation: action.situation,
        myCards: action.your_cards,
        roundId: action.round_id,
        roundNumber: action.round_number,
        czarId: action.czar_id,
        isCzar: action.is_czar,
        timer: action.timer,
        timerPhase: 'play',
        plays: [],
        roundResult: null,
        playedIds: new Set(),
        votedThisRound: false,
      }

    case 'PLAYER_PLAYED':
      return { ...state, playedIds: new Set([...state.playedIds, action.player_id]) }

    case 'VOTING_STARTED':
      return {
        ...state,
        phase: 'voting',
        plays: action.plays,
        timer: action.timer,
        timerPhase: 'vote',
      }

    case 'VOTE_CAST':
      return {
        ...state,
        votedThisRound: action.voter_id === state.playerId ? true : state.votedThisRound,
      }

    case 'ROUND_RESULT':
      return {
        ...state,
        phase: 'results',
        roundResult: action,
      }

    case 'GAME_OVER':
      return { ...state, phase: 'game_over', gameOver: action }

    case 'TIMER_TICK':
      return { ...state, timer: action.seconds, timerPhase: action.phase }

    case 'CARDS_RECEIVED':
      return { ...state, myCards: [...state.myCards, ...action.cards] }

    case 'CARD_PLAYED_LOCAL':
      return {
        ...state,
        myCards: state.myCards.filter((c) => c.card_id !== action.card_id),
      }

    case 'RESET':
      return initialState

    default:
      return state
  }
}

export function GameProvider({ children }) {
  const [state, dispatch] = useReducer(gameReducer, initialState)

  const setRoom = useCallback((roomCode, playerId) => {
    dispatch({ type: 'SET_ROOM', roomCode, playerId })
  }, [])

  const handleWsMessage = useCallback((msg) => {
    const { type, payload } = msg
    switch (type) {
      case 'room_updated':
        dispatch({ type: 'ROOM_UPDATED', ...payload })
        break
      case 'game_started':
        dispatch({ type: 'GAME_STARTED' })
        break
      case 'situation_dealt':
        dispatch({ type: 'SITUATION_DEALT', ...payload })
        break
      case 'player_played':
        dispatch({ type: 'PLAYER_PLAYED', ...payload })
        break
      case 'voting_started':
        dispatch({ type: 'VOTING_STARTED', ...payload })
        break
      case 'vote_cast':
        dispatch({ type: 'VOTE_CAST', ...payload })
        break
      case 'round_result':
        dispatch({ type: 'ROUND_RESULT', ...payload })
        break
      case 'game_over':
        dispatch({ type: 'GAME_OVER', ...payload })
        break
      case 'timer_tick':
        dispatch({ type: 'TIMER_TICK', ...payload })
        break
      case 'cards_received':
        dispatch({ type: 'CARDS_RECEIVED', ...payload })
        break
      default:
        break
    }
  }, [])

  const playCardLocal = useCallback((cardId) => {
    dispatch({ type: 'CARD_PLAYED_LOCAL', card_id: cardId })
  }, [])

  const reset = useCallback(() => dispatch({ type: 'RESET' }), [])

  return (
    <GameContext.Provider value={{ state, setRoom, handleWsMessage, playCardLocal, reset, dispatch }}>
      {children}
    </GameContext.Provider>
  )
}

export const useGame = () => useContext(GameContext)
