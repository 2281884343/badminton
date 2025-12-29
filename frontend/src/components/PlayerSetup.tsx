import { useState, useEffect } from 'react'
import { PlayerProfile } from '../App'
import { API_BASE_URL } from '../config'

interface Props {
  onComplete: (profile: PlayerProfile) => void
}

const SKILLS = [
  "发球", "接发球", "高远球", "杀球", "吊球", 
  "挑球", "放网", "扑球", "勾球", "搓球"
]

function PlayerSetup({ onComplete }: Props) {
  const [username, setUsername] = useState('')
  const [skills, setSkills] = useState<{ [key: string]: number }>({})
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    // 初始化技能为0
    const initialSkills: { [key: string]: number } = {}
    SKILLS.forEach(skill => {
      initialSkills[skill] = 0
    })
    setSkills(initialSkills)
  }, [])

  const loadPlayer = async () => {
    if (!username.trim()) {
      alert('请输入用户名')
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/player/${username}`)
      const data = await response.json()
      
      if (data.skills) {
        setSkills(data.skills)
      }
    } catch (error) {
      console.error('加载玩家失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const savePlayer = async () => {
    if (!username.trim()) {
      alert('请输入用户名')
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/player/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, skills }),
      })

      if (response.ok) {
        alert('保存成功！')
        onComplete({ username, skills })
      }
    } catch (error) {
      console.error('保存失败:', error)
      alert('保存失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  const handleSkillChange = (skill: string, value: number) => {
    setSkills(prev => ({
      ...prev,
      [skill]: Math.max(-100, Math.min(100, value))
    }))
  }

  return (
    <div>
      <h2>玩家配置</h2>
      
      <div style={{ marginBottom: '30px' }}>
        <label style={{ display: 'block', marginBottom: '10px', fontWeight: 'bold' }}>
          用户名：
        </label>
        <div style={{ display: 'flex', gap: '10px' }}>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="输入用户名"
            style={{ flex: 1 }}
          />
          <button onClick={loadPlayer} disabled={loading}>
            加载配置
          </button>
        </div>
      </div>

      <h3>技术熟练度设置（-100 到 100）</h3>
      <p style={{ color: '#666', marginBottom: '20px' }}>
        -100表示完全不会，0表示一般水平，100表示完全掌握
      </p>

      <div className="skill-grid">
        {SKILLS.map(skill => (
          <div key={skill} className="skill-item">
            <label>{skill}</label>
            <input
              type="number"
              min="-100"
              max="100"
              value={skills[skill] || 0}
              onChange={(e) => handleSkillChange(skill, parseInt(e.target.value) || 0)}
            />
            <div style={{ fontSize: '12px', color: '#888' }}>
              当前: {skills[skill] || 0}
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: '30px', textAlign: 'center' }}>
        <button 
          onClick={savePlayer} 
          disabled={loading || !username.trim()}
          style={{ padding: '15px 40px', fontSize: '18px' }}
        >
          {loading ? '处理中...' : '保存并进入游戏'}
        </button>
      </div>

      <div style={{ marginTop: '20px', padding: '15px', background: '#f0f0f0', borderRadius: '8px' }}>
        <h4>说明：</h4>
        <ul style={{ marginLeft: '20px', lineHeight: '1.8' }}>
          <li>熟练度≥80：大失败需要连续投两次1</li>
          <li>熟练度≥90：大成功判定从20变为19</li>
          <li>每30点熟练度增加1点随机数浮动</li>
          <li>负熟练度会减少最终随机数</li>
        </ul>
      </div>
    </div>
  )
}

export default PlayerSetup

