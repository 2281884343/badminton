# 🏸 羽毛球游戏

一个基于跑团机制的羽毛球在线对战游戏，支持单打和双打模式，采用随机数判定系统配合AI描述生成，为玩家带来独特的游戏体验。

## ✨ 功能特点

- 🎮 **双模式支持**：1v1单打和2v2双打
- 🎲 **跑团式判定**：基于随机数（1-20）的击球判定系统
- 🤖 **AI解说**：每一球都由AI生成生动的比赛描述
- 📊 **技能系统**：10种羽毛球技术动作，每个动作可独立设置熟练度（-100到100）
- 🌐 **网络对战**：基于WebSocket的实时在线对战
- 💾 **数据持久化**：自动保存玩家配置和技能熟练度

## 🎯 游戏规则

### 基础规则

1. **随机数判定**：每次击球投掷1-20的随机数
   - `1` = 大失败，这一球绝对失分
   - `20` = 大成功，球质量非常高（杀球直接得分）
   - `15+` = 高质量球
   - `9-` = 低质量球

2. **难度判定**：
   - 高质量球（≥15）：对方需要达到原数值的2/3才能接住
   - 低质量球（<9）：对方下一球获得加成（己方随机数的1/4）

3. **技能熟练度效果**：
   - **≥80**：大失败需要连续投两次1
   - **≥90**：大成功判定从20变为19
   - **每30点**：增加1点随机数浮动上限
   - **负熟练度**：会减少最终随机数

4. **计分规则**：21分制

## 🛠️ 技术栈

### 后端
- Python 3.8+
- FastAPI
- WebSocket
- OpenAI SDK (Moonshot AI)

### 前端
- React 18
- TypeScript
- Vite
- WebSocket

## 📦 安装和运行

### 环境要求

- Linux服务器（Ubuntu 20.04+ / CentOS 8+ / Debian 11+）
- Python 3.8+
- Node.js 16+
- Nginx（生产环境推荐）

### 快速部署

1. **自动部署**（推荐）

```bash
# 赋予执行权限
chmod +x deploy.sh start-dev.sh start-prod.sh

# 运行部署脚本
./deploy.sh
```

2. **启动服务**

开发模式：
```bash
./start-dev.sh
```

生产模式：
```bash
./start-prod.sh
```

3. **使用systemd服务**（推荐生产环境）

```bash
# 修改badminton-game.service中的路径
sudo cp badminton-game.service /etc/systemd/system/
sudo systemctl enable badminton-game
sudo systemctl start badminton-game
```

详细部署步骤请查看：[部署指南-Linux.md](./部署指南-Linux.md)

### 手动安装

#### 后端设置

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir -p data/players
python main.py
```

#### 前端设置

```bash
cd frontend
npm install
npm run dev  # 开发模式
# 或
npm run build  # 生产构建
```

## 🎮 使用说明

### 1. 玩家配置

首次进入游戏时，需要配置玩家信息：

- 输入**用户名**
- 设置**10种技术动作**的熟练度（-100到100）
  - 发球、接发球、高远球、杀球、吊球
  - 挑球、放网、扑球、勾球、搓球
- 点击"保存并进入游戏"

配置会自动保存到 `backend/data/players/{username}.json`

### 2. 创建/加入房间

- 选择**单打（1v1）**或**双打（2v2）**模式
- 点击"创建房间"或输入房间ID加入已有房间

### 3. 开始游戏

- 等待足够的玩家加入（单打需要2人，双打需要4人）
- 点击"开始游戏"

### 4. 进行比赛

1. 在你的回合时：
   - 从下拉菜单选择**技术动作**
   - （可选）输入**对话内容**与AI交互
   - 点击"**击球！**"按钮

2. 系统会：
   - 投掷随机数
   - 根据你的技能熟练度调整数值
   - 应用高/低质量球规则
   - 调用AI生成这一球的描述
   - 判断是否得分

3. 比赛记录会实时显示：
   - 基础随机数、调整后数值、最终数值
   - 球的质量（大失败/低质量/普通/高质量/大成功）
   - AI生成的解说描述
   - 得分情况

4. 达到21分后游戏结束

## 📂 项目结构

```
bm/
├── backend/
│   ├── main.py              # FastAPI主程序
│   ├── requirements.txt     # Python依赖
│   └── data/
│       └── players/         # 玩家配置文件存储
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # 主应用组件
│   │   ├── main.tsx         # 入口文件
│   │   ├── index.css        # 全局样式
│   │   └── components/
│   │       ├── PlayerSetup.tsx    # 玩家配置页面
│   │       ├── GameLobby.tsx      # 游戏大厅
│   │       └── GameRoom.tsx       # 游戏房间
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── index.html
└── README.md
```

## 🔧 配置说明

### AI API配置

游戏使用 Moonshot AI (Kimi) 生成比赛描述。API密钥已在代码中配置：

```python
# backend/main.py
client = OpenAI(
    api_key="sk-r7lK62mQRVGX0Qqh9k6bZsS4KeCTbF7YKonjuDZci9k8vj2r",
    base_url="https://api.moonshot.cn/v1",
)
```

如需更换API密钥，请修改 `backend/main.py` 中的 `api_key` 字段。

### WebSocket配置

默认配置：
- 后端WebSocket: `ws://localhost:8080/ws`
- 前端通过Vite代理自动转发

如需修改端口，请同时更新：
- `backend/main.py` 最后一行的端口
- `frontend/vite.config.ts` 中的proxy配置

## 🎯 技术动作说明

游戏包含10种羽毛球技术动作：

1. **发球**：开球动作
2. **接发球**：接对方发球
3. **高远球**：后场高吊至对方后场
4. **杀球**：大力扣杀，大成功直接得分
5. **吊球**：轻吊至对方网前
6. **挑球**：网前挑至后场
7. **放网**：网前轻放
8. **扑球**：网前快速扑压
9. **勾球**：网前对角勾球
10. **搓球**：网前搓球过网

## 📊 数据文件格式

玩家配置文件（JSON格式）：

```json
{
  "username": "玩家名称",
  "skills": {
    "发球": 50,
    "接发球": 60,
    "高远球": 70,
    "杀球": 80,
    "吊球": 65,
    "挑球": 55,
    "放网": 45,
    "扑球": 40,
    "勾球": 35,
    "搓球": 30
  },
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

## 🐛 常见问题

### 1. WebSocket连接失败
- 确保后端服务已启动
- 检查防火墙设置
- 确认端口8080未被占用

### 2. AI描述生成失败
- 检查API密钥是否有效
- 确认网络连接正常
- 系统会自动降级为简单描述

### 3. 玩家配置加载失败
- 确保 `backend/data/players/` 目录存在
- 检查JSON文件格式是否正确

## 📝 开发说明

### 添加新技术动作

1. 在 `backend/main.py` 中的 `SKILLS` 列表添加新动作
2. 在 `frontend/src/components/PlayerSetup.tsx` 中同步更新

### 修改游戏规则

主要游戏逻辑在 `backend/main.py` 的以下函数中：
- `calculate_shot_result()`: 计算击球结果
- `can_receive_shot()`: 判断是否能接住
- `generate_ai_description()`: 生成AI描述

## 📄 许可证

本项目仅供学习和娱乐使用。

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📞 联系方式

如有问题或建议，请通过GitHub Issues联系。

---

**祝你游戏愉快！🏸**

