import { useState } from 'react'
import { PlayerProfile } from '../App'

interface Props {
  playerProfile: PlayerProfile
  onJoinRoom: (roomId: string, mode: '2p' | '4p') => void
}

function GameLobby({ playerProfile, onJoinRoom }: Props) {
  const [selectedMode, setSelectedMode] = useState<'2p' | '4p'>('2p')
  const [roomId, setRoomId] = useState('')
  const [loading, setLoading] = useState(false)

  const createRoom = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/room/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ mode: selectedMode }),
      })
      
      const data = await response.json()
      onJoinRoom(data.room_id, selectedMode)
    } catch (error) {
      console.error('创建房间失败:', error)
      alert('创建房间失败')
    } finally {
      setLoading(false)
    }
  }

  const joinRoom = () => {
    if (!roomId.trim()) {
      alert('请输入房间ID')
      return
    }
    onJoinRoom(roomId, selectedMode)
  }

  return (
    <div>
      <h2>欢迎，{playerProfile.username}！</h2>

      <div className="mode-selector">
        <div 
          className={`mode-card ${selectedMode === '2p' ? 'selected' : ''}`}
          onClick={() => setSelectedMode('2p')}
        >
          <h3>单打模式</h3>
          <p>1 vs 1</p>
          <p style={{ fontSize: '48px', margin: '20px 0' }}>🏸</p>
        </div>

        <div 
          className={`mode-card ${selectedMode === '4p' ? 'selected' : ''}`}
          onClick={() => setSelectedMode('4p')}
        >
          <h3>双打模式</h3>
          <p>2 vs 2</p>
          <p style={{ fontSize: '48px', margin: '20px 0' }}>🏸🏸</p>
        </div>
      </div>

      <div style={{ textAlign: 'center', marginTop: '40px' }}>
        <button 
          onClick={createRoom} 
          disabled={loading}
          style={{ padding: '15px 40px', fontSize: '18px', marginBottom: '20px' }}
        >
          创建{selectedMode === '2p' ? '单打' : '双打'}房间
        </button>

        <div style={{ margin: '30px 0' }}>
          <p style={{ color: '#666', marginBottom: '10px' }}>或者</p>
        </div>

        <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', maxWidth: '400px', margin: '0 auto' }}>
          <input
            type="text"
            value={roomId}
            onChange={(e) => setRoomId(e.target.value)}
            placeholder="输入房间ID"
            style={{ flex: 1 }}
          />
          <button onClick={joinRoom}>
            加入房间
          </button>
        </div>
      </div>

      <div style={{ marginTop: '40px', padding: '20px', background: '#f9f9f9', borderRadius: '8px' }}>
        <h3>你的技能等级：</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '10px', marginTop: '15px' }}>
          {Object.entries(playerProfile.skills).map(([skill, level]) => (
            <div key={skill} style={{ 
              padding: '10px', 
              background: level > 50 ? '#d4edda' : level < -50 ? '#f8d7da' : 'white',
              borderRadius: '6px',
              border: '1px solid #ddd'
            }}>
              <strong>{skill}:</strong> {level}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default GameLobby

