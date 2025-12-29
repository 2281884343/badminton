import { useState, useEffect } from 'react'
import PlayerSetup from './components/PlayerSetup'
import GameLobby from './components/GameLobby'
import GameRoom from './components/GameRoom'

export type GameState = 'setup' | 'lobby' | 'game'

export interface PlayerProfile {
  username: string
  skills: { [key: string]: number }
}

function App() {
  const [gameState, setGameState] = useState<GameState>('setup')
  const [playerProfile, setPlayerProfile] = useState<PlayerProfile | null>(null)
  const [roomId, setRoomId] = useState<string>('')
  const [gameMode, setGameMode] = useState<'2p' | '4p'>('2p')

  const handlePlayerSetup = (profile: PlayerProfile) => {
    setPlayerProfile(profile)
    setGameState('lobby')
  }

  const handleJoinRoom = (rid: string, mode: '2p' | '4p') => {
    setRoomId(rid)
    setGameMode(mode)
    setGameState('game')
  }

  const handleLeaveRoom = () => {
    setRoomId('')
    setGameState('lobby')
  }

  return (
    <div className="container">
      <h1 style={{ textAlign: 'center', fontSize: '36px' }}>🏸 羽毛球游戏</h1>
      
      {gameState === 'setup' && (
        <PlayerSetup onComplete={handlePlayerSetup} />
      )}
      
      {gameState === 'lobby' && playerProfile && (
        <GameLobby 
          playerProfile={playerProfile} 
          onJoinRoom={handleJoinRoom}
        />
      )}
      
      {gameState === 'game' && playerProfile && roomId && (
        <GameRoom
          playerProfile={playerProfile}
          roomId={roomId}
          gameMode={gameMode}
          onLeave={handleLeaveRoom}
        />
      )}
    </div>
  )
}

export default App

