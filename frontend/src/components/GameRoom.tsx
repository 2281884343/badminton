import { useState, useEffect, useRef } from 'react'
import { PlayerProfile } from '../App'

interface Props {
  playerProfile: PlayerProfile
  roomId: string
  gameMode: '2p' | '4p'
  onLeave: () => void
}

interface GameState {
  status: string
  current_server: string | null
  current_receiver: string | null
  score_a: number
  score_b: number
  last_shot_quality: string | null
  last_shot_value: number | null
  is_first_shot?: boolean
  rally_count?: number
}

interface LogEntry {
  type: string
  player?: string
  skill?: string
  message?: string
  result?: any
  description?: string
  scored?: boolean
  timestamp: number
}

const SKILLS = [
  "发球", "接发球", "高远球", "杀球", "吊球", 
  "挑球", "放网", "扑球", "勾球", "搓球"
]

function GameRoom({ playerProfile, roomId, gameMode, onLeave }: Props) {
  const [ws, setWs] = useState<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)
  const [players, setPlayers] = useState<string[]>([])
  const [gameState, setGameState] = useState<GameState>({
    status: 'waiting',
    current_server: null,
    current_receiver: null,
    score_a: 0,
    score_b: 0,
    last_shot_quality: null,
    last_shot_value: null,
    is_first_shot: true,
    rally_count: 0
  })
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [selectedSkill, setSelectedSkill] = useState(SKILLS[0])
  const [chatMessage, setChatMessage] = useState('')
  const [isShooting, setIsShooting] = useState(false)
  
  const logRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // 连接WebSocket - 自动适配生产环境和开发环境
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.hostname
    const port = '8080'  // 后端统一使用 8080 端口
    const wsUrl = `${protocol}//${host}:${port}/ws/${roomId}/${playerProfile.username}`
    const websocket = new WebSocket(wsUrl)

    websocket.onopen = () => {
      console.log('WebSocket连接成功')
      setConnected(true)
    }

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data)
      handleMessage(data)
    }

    websocket.onerror = (error) => {
      console.error('WebSocket错误:', error)
      alert('连接失败，请检查后端是否运行')
    }

    websocket.onclose = () => {
      console.log('WebSocket连接关闭')
      setConnected(false)
    }

    setWs(websocket)

    return () => {
      websocket.close()
    }
  }, [roomId, playerProfile.username])

  useEffect(() => {
    // 自动滚动到最新日志
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [logs])

  const handleMessage = (data: any) => {
    console.log('收到消息:', data)

    switch (data.type) {
      case 'player_joined':
        setPlayers(data.players)
        addLog({ type: 'system', message: `${data.username} 加入了房间`, timestamp: Date.now() })
        break

      case 'player_left':
        setPlayers(data.players)
        addLog({ type: 'system', message: `${data.username} 离开了房间`, timestamp: Date.now() })
        break

      case 'game_started':
        setGameState(data.game_state)
        addLog({ type: 'system', message: '游戏开始！', timestamp: Date.now() })
        break

      case 'game_restarted':
        setGameState(data.game_state)
        setLogs([])  // 清空日志
        addLog({ type: 'system', message: '重新开始游戏！', timestamp: Date.now() })
        break

      case 'shot_result':
        setIsShooting(false)
        addLog({
          type: 'shot',
          player: data.player,
          skill: data.skill,
          message: data.message,
          result: data.result,
          description: data.description,
          scored: data.scored,
          timestamp: Date.now()
        })
        
        if (data.game_state) {
          setGameState(data.game_state)
        }
        
        if (data.game_over) {
          addLog({ type: 'system', message: '游戏结束！', timestamp: Date.now() })
        }
        break

      case 'error':
        alert(data.message)
        break
    }
  }

  const addLog = (log: LogEntry) => {
    setLogs(prev => [...prev, log])
  }

  const startGame = () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'start_game' }))
    }
  }

  const restartGame = () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'restart_game' }))
    }
  }

  const performShot = () => {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      alert('未连接到服务器')
      return
    }

    if (isShooting) {
      return
    }

    setIsShooting(true)
    ws.send(JSON.stringify({
      type: 'shot',
      skill: selectedSkill,
      message: chatMessage
    }))

    setChatMessage('')
  }

  const getQualityColor = (quality: string) => {
    switch (quality) {
      case 'critical_fail': return '#dc3545'
      case 'low': return '#ffc107'
      case 'normal': return '#17a2b8'
      case 'high': return '#28a745'
      case 'critical_success': return '#6f42c1'
      default: return '#333'
    }
  }

  const getQualityText = (quality: string) => {
    switch (quality) {
      case 'critical_fail': return '大失败'
      case 'low': return '低质量'
      case 'normal': return '普通'
      case 'high': return '高质量'
      case 'critical_success': return '大成功'
      default: return quality
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2>🏠 房间号: <span style={{ color: '#667eea', fontSize: '32px', fontWeight: 'bold' }}>{roomId}</span></h2>
          <p style={{ color: '#666', marginTop: '10px' }}>
            {gameMode === '2p' ? '单打模式' : '双打模式'} | 
            状态: {connected ? '✅ 已连接' : '❌ 未连接'}
          </p>
        </div>
        <button onClick={onLeave} style={{ background: '#dc3545' }}>
          离开房间
        </button>
      </div>

      {/* 比分板 */}
      <div className="score-board">
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '16px', marginBottom: '10px' }}>队伍 A</div>
          <div>{gameState.score_a}</div>
        </div>
        <div style={{ fontSize: '24px' }}>VS</div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '16px', marginBottom: '10px' }}>队伍 B</div>
          <div>{gameState.score_b}</div>
        </div>
      </div>

      {/* 玩家列表 */}
      <div className="players-list">
        {players.map((player, index) => (
          <div key={player} className="player-card">
            <strong>{player}</strong>
            {player === playerProfile.username && ' (你)'}
            <div style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
              队伍 {index < (gameMode === '2p' ? 1 : 2) ? 'A' : 'B'}
            </div>
          </div>
        ))}
      </div>

      {/* 等待区 */}
      {gameState.status === 'waiting' && (
        <div className="waiting-room">
          <p style={{ fontSize: '18px', marginBottom: '20px' }}>
            等待玩家加入... ({players.length}/{gameMode === '2p' ? 2 : 4})
          </p>
          {players.length >= (gameMode === '2p' ? 2 : 2) && (
            <button 
              onClick={startGame}
              style={{ padding: '15px 40px', fontSize: '18px' }}
            >
              开始游戏
            </button>
          )}
        </div>
      )}

      {/* 游戏区 */}
      {gameState.status === 'playing' && (
        <div>
          <div className="chat-box">
            <h3>对话与击球</h3>
            <p style={{ color: '#666', fontSize: '14px', marginBottom: '15px' }}>
              选择技术动作，输入对话（可选），然后点击击球按钮
            </p>
            
            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                选择技术动作：{gameState.is_first_shot && <span style={{ color: '#dc3545' }}> (第一球必须发球)</span>}
              </label>
              <select 
                value={selectedSkill}
                onChange={(e) => setSelectedSkill(e.target.value)}
                style={{ 
                  padding: '10px', 
                  width: '100%', 
                  border: '2px solid #e0e0e0', 
                  borderRadius: '6px',
                  fontSize: '16px'
                }}
              >
                {(gameState.is_first_shot ? ["发球"] : SKILLS).map(skill => (
                  <option key={skill} value={skill}>
                    {skill} (熟练度: {playerProfile.skills[skill] || 0})
                  </option>
                ))}
              </select>
            </div>

            <div className="chat-input">
              <input
                type="text"
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                placeholder="输入对话内容（可选）"
                onKeyPress={(e) => e.key === 'Enter' && performShot()}
              />
              <button 
                onClick={performShot} 
                disabled={isShooting || !connected}
                style={{ minWidth: '100px' }}
              >
                {isShooting ? '击球中...' : '击球！'}
              </button>
            </div>
          </div>

          {/* 游戏日志 */}
          <div className="game-log" ref={logRef}>
            <h3>比赛记录</h3>
            {logs.map((log, index) => (
              <div key={index} className="log-entry">
                {log.type === 'system' && (
                  <div style={{ color: '#667eea', fontWeight: 'bold' }}>
                    ⚡ {log.message}
                  </div>
                )}
                
                {log.type === 'shot' && log.result && (
                  <div>
                    <div style={{ marginBottom: '8px' }}>
                      <strong style={{ color: '#667eea' }}>{log.player}</strong> 
                      {' '}- {log.skill}
                      {log.message && <span style={{ color: '#888' }}>: "{log.message}"</span>}
                    </div>
                    
                    <div style={{ 
                      background: '#f9f9f9', 
                      padding: '10px', 
                      borderRadius: '6px',
                      marginBottom: '8px'
                    }}>
                      <div style={{ display: 'flex', gap: '15px', fontSize: '14px' }}>
                        <span>🎲 基础: {log.result.base_roll}</span>
                        <span>📊 调整: {log.result.adjusted_roll}</span>
                        <span>✨ 最终: <strong>{log.result.final_roll}</strong></span>
                        <span style={{ 
                          color: getQualityColor(log.result.quality),
                          fontWeight: 'bold'
                        }}>
                          {getQualityText(log.result.quality)}
                        </span>
                      </div>
                      {log.result.low_quality_bonus > 0 && (
                        <div style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
                          对方低质量球加成: +{log.result.low_quality_bonus}
                        </div>
                      )}
                    </div>
                    
                    <div style={{ 
                      fontStyle: 'italic', 
                      color: '#555',
                      background: '#fff3cd',
                      padding: '8px',
                      borderRadius: '4px',
                      borderLeft: '3px solid #ffc107'
                    }}>
                      🎙️ {log.description}
                    </div>
                    
                    {log.scored && (
                      <div style={{ 
                        marginTop: '8px', 
                        color: '#28a745', 
                        fontWeight: 'bold',
                        fontSize: '16px'
                      }}>
                        🎯 得分！
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 游戏结束 */}
      {gameState.status === 'finished' && (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <h2 style={{ fontSize: '36px', marginBottom: '20px' }}>
            🏆 游戏结束！
          </h2>
          <p style={{ fontSize: '24px', marginBottom: '30px' }}>
            最终比分: {gameState.score_a} - {gameState.score_b}
          </p>
          <p style={{ fontSize: '18px', color: '#666', marginBottom: '40px' }}>
            {gameState.score_a > gameState.score_b ? '队伍 A 获胜！' : '队伍 B 获胜！'}
          </p>
          <div style={{ display: 'flex', gap: '20px', justifyContent: 'center' }}>
            <button 
              onClick={restartGame}
              style={{ padding: '15px 40px', fontSize: '18px', background: '#28a745' }}
            >
              再来一局
            </button>
            <button 
              onClick={onLeave}
              style={{ padding: '15px 40px', fontSize: '18px', background: '#6c757d' }}
            >
              返回大厅
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default GameRoom

