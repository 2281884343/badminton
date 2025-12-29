from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import json
import random
import asyncio
from datetime import datetime
from openai import OpenAI
import os

app = FastAPI()

# CORS设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化AI客户端
# 优先使用环境变量，否则使用默认密钥
MOONSHOT_API_KEY = os.getenv(
    "MOONSHOT_API_KEY",
    "sk-r7lK62mQRVGX0Qqh9k6bZsS4KeCTbF7YKonjuDZci9k8vj2r"
)

client = OpenAI(
    api_key=MOONSHOT_API_KEY,
    base_url="https://api.moonshot.cn/v1",
)

# 技术动作列表
SKILLS = [
    "发球", "接发球", "高远球", "杀球", "吊球", 
    "挑球", "放网", "扑球", "勾球", "搓球"
]

# 游戏房间管理
class GameRoom:
    def __init__(self, room_id: str, mode: str):
        self.room_id = room_id
        self.mode = mode  # "2p" or "4p"
        self.players: Dict[str, dict] = {}
        self.websockets: Dict[str, WebSocket] = {}
        self.game_state = {
            "status": "waiting",  # waiting, playing, finished
            "current_server": None,
            "current_receiver": None,
            "score_a": 0,
            "score_b": 0,
            "last_shot_quality": None,
            "last_shot_value": None,
            "rally_history": [],
            "is_first_shot": True,  # 是否是第一球（必须发球）
            "rally_count": 0  # 回合计数
        }

rooms: Dict[str, GameRoom] = {}

# 数据模型
class PlayerProfile(BaseModel):
    username: str
    skills: Dict[str, int]  # 技能名称: 熟练度(-100到100)

class ShotAction(BaseModel):
    room_id: str
    player_name: str
    skill: str
    message: str

# 玩家配置文件管理
def load_player_profile(username: str) -> Optional[Dict]:
    """从文件加载玩家配置"""
    filename = f"data/players/{username}.json"
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_player_profile(username: str, skills: Dict[str, int]):
    """保存玩家配置到文件"""
    os.makedirs("data/players", exist_ok=True)
    filename = f"data/players/{username}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            "username": username,
            "skills": skills,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)

# API端点
@app.post("/api/player/save")
async def save_player(profile: PlayerProfile):
    """保存玩家配置"""
    save_player_profile(profile.username, profile.skills)
    return {"status": "success", "message": "玩家配置已保存"}

@app.get("/api/player/{username}")
async def get_player(username: str):
    """获取玩家配置"""
    profile = load_player_profile(username)
    if profile:
        return profile
    return {"username": username, "skills": {skill: 0 for skill in SKILLS}}

@app.get("/api/skills")
async def get_skills():
    """获取所有技能列表"""
    return {"skills": SKILLS}

class CreateRoomRequest(BaseModel):
    mode: str

@app.post("/api/room/create")
async def create_room(request: CreateRoomRequest):
    """创建游戏房间"""
    # 生成简短的房间ID（6位随机数字）
    room_id = str(random.randint(100000, 999999))
    # 如果房间ID已存在，重新生成
    while room_id in rooms:
        room_id = str(random.randint(100000, 999999))
    rooms[room_id] = GameRoom(room_id, request.mode)
    return {"room_id": room_id, "mode": request.mode}

@app.get("/api/rooms")
async def list_rooms():
    """列出所有房间"""
    return {
        "rooms": [
            {
                "room_id": room.room_id,
                "mode": room.mode,
                "players": len(room.players),
                "status": room.game_state["status"]
            }
            for room in rooms.values()
        ]
    }

# 游戏逻辑函数
def calculate_shot_result(base_roll: int, skill_level: int, is_low_quality_bonus: int = 0) -> dict:
    """
    计算击球结果
    :param base_roll: 基础随机数(1-20)
    :param skill_level: 技能熟练度(-100到100)
    :param is_low_quality_bonus: 对方低质量球的加成
    :return: 包含最终数值和各种判定信息的字典
    """
    # 计算熟练度浮动
    float_range = abs(skill_level) // 30
    if float_range > 0:
        float_value = random.randint(0, float_range)
        if skill_level >= 0:
            adjusted_roll = base_roll + float_value
        else:
            adjusted_roll = base_roll - float_value
    else:
        adjusted_roll = base_roll
    
    # 添加低质量球加成
    final_roll = adjusted_roll + is_low_quality_bonus
    
    # 判定是否为大失败
    is_critical_fail = False
    if skill_level >= 80:
        # 需要两次都是1才大失败
        second_roll = random.randint(1, 20)
        is_critical_fail = (base_roll == 1 and second_roll == 1)
    else:
        is_critical_fail = (base_roll == 1)
    
    # 判定是否为大成功
    is_critical_success = False
    critical_threshold = 19 if skill_level >= 90 else 20
    is_critical_success = (base_roll >= critical_threshold)
    
    # 判定球的质量
    quality = "normal"
    if is_critical_fail or final_roll <= 1:
        quality = "critical_fail"
    elif is_critical_success:
        quality = "critical_success"
    elif final_roll >= 15:
        quality = "high"
    elif final_roll < 9:
        quality = "low"
    
    return {
        "base_roll": base_roll,
        "adjusted_roll": adjusted_roll,
        "final_roll": final_roll,
        "quality": quality,
        "is_critical_fail": is_critical_fail,
        "is_critical_success": is_critical_success,
        "skill_level": skill_level,
        "low_quality_bonus": is_low_quality_bonus
    }

def can_receive_shot(defense_result: dict, attack_quality: str, attack_final_roll: int) -> bool:
    """
    判断是否能接住球
    :param defense_result: 防守方的击球结果
    :param attack_quality: 进攻方的球质量
    :param attack_final_roll: 进攻方的最终随机数
    :return: 是否接住
    """
    # 大失败直接接不住
    if defense_result["is_critical_fail"] or defense_result["final_roll"] <= 1:
        return False
    
    # 对方大成功直接得分
    if attack_quality == "critical_success":
        return False
    
    # 高质量球需要达到2/3才能接住
    if attack_quality == "high":
        required = attack_final_roll * 2 // 3
        return defense_result["final_roll"] >= required
    
    # 普通球和低质量球都能接住
    return True

async def generate_ai_description(skill: str, result: dict, game_state: dict) -> str:
    """
    调用AI生成击球描述
    :param skill: 使用的技能
    :param result: 击球结果
    :param game_state: 游戏状态
    :return: AI生成的描述
    """
    try:
        score_a = game_state.get("score_a", 0)
        score_b = game_state.get("score_b", 0)
        
        # 质量等级说明
        quality_map = {
            "critical_fail": "大失败（最差）",
            "low": "低质量（较差）",
            "normal": "普通",
            "high": "高质量（优秀）",
            "critical_success": "大成功（完美）"
        }
        quality_desc = quality_map.get(result['quality'], result['quality'])
        
        prompt = f"""你是一个专业的羽毛球比赛解说员。请用15-20字描述这一球的情况。

技术动作：{skill}
球的质量：{quality_desc}
随机数值：{result['final_roll']}（满分20分）
当前比分：{score_a}:{score_b}

【重要规则】：
1. 必须严格根据"球的质量"来描述：
   - 大失败：必须用负面词汇，如"失误、下网、出界、没接到"
   - 低质量：必须用较差词汇，如"勉强、质量不佳、回球软弱"
   - 普通：中性词汇，如"稳健、常规"
   - 高质量：积极词汇，如"漂亮、精准、有威胁"
   - 大成功：极度赞美词汇，如"完美、绝杀、神仙球"
2. 描述必须与质量等级完全匹配，不能出现"低质量球但描述很棒"的情况
3. 简洁生动，15-20字
4. 如果是关键分可以增加紧张感

只返回描述文字，不要其他内容。"""

        completion = client.chat.completions.create(
            model="kimi-k2-turbo-preview",
            messages=[
                {"role": "system", "content": "你是一个严谨的羽毛球比赛解说员，必须根据球的实际质量给出相应的描述，绝不能夸大或美化低质量的球。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,  # 降低温度提高准确性
            max_tokens=60
        )
        
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"AI生成失败: {e}")
        # 降级方案
        quality_desc = {
            "critical_fail": "严重失误！球直接下网",
            "low": "回球质量不佳，对方机会来了",
            "normal": "稳健回击，保持节奏",
            "high": "漂亮的一球！很有威胁",
            "critical_success": "完美击球！无懈可击！"
        }
        return quality_desc.get(result['quality'], f"{skill}完成")


# WebSocket连接管理
@app.websocket("/ws/{room_id}/{username}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, username: str):
    await websocket.accept()
    
    if room_id not in rooms:
        await websocket.send_json({"type": "error", "message": "房间不存在"})
        await websocket.close()
        return
    
    room = rooms[room_id]
    
    # 加载玩家配置
    player_profile = load_player_profile(username)
    if not player_profile:
        await websocket.send_json({"type": "error", "message": "请先配置玩家信息"})
        await websocket.close()
        return
    
    # 添加玩家到房间
    room.players[username] = player_profile
    room.websockets[username] = websocket
    
    # 通知所有人有新玩家加入
    await broadcast_to_room(room, {
        "type": "player_joined",
        "username": username,
        "players": list(room.players.keys()),
        "player_count": len(room.players)
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            await handle_game_action(room, username, data)
    except WebSocketDisconnect:
        del room.players[username]
        del room.websockets[username]
        await broadcast_to_room(room, {
            "type": "player_left",
            "username": username,
            "players": list(room.players.keys())
        })

async def broadcast_to_room(room: GameRoom, message: dict):
    """向房间内所有玩家广播消息"""
    for ws in room.websockets.values():
        try:
            await ws.send_json(message)
        except:
            pass

async def handle_game_action(room: GameRoom, username: str, data: dict):
    """处理游戏动作"""
    action_type = data.get("type")
    
    if action_type == "start_game" or action_type == "restart_game":
        # 开始游戏或重新开始
        room.game_state["status"] = "playing"
        room.game_state["current_server"] = list(room.players.keys())[0]
        room.game_state["current_receiver"] = list(room.players.keys())[1] if len(room.players) > 1 else None
        room.game_state["score_a"] = 0
        room.game_state["score_b"] = 0
        room.game_state["last_shot_quality"] = None
        room.game_state["last_shot_value"] = None
        room.game_state["is_first_shot"] = True
        room.game_state["rally_count"] = 0
        room.game_state["rally_history"] = []
        
        await broadcast_to_room(room, {
            "type": "game_started" if action_type == "start_game" else "game_restarted",
            "game_state": room.game_state
        })
    
    elif action_type == "shot":
        # 玩家击球
        skill = data.get("skill")
        message = data.get("message", "")
        
        # 检查第一球必须是发球
        if room.game_state.get("is_first_shot", False) and skill != "发球":
            await room.websockets[username].send_json({
                "type": "error",
                "message": "每回合第一球必须是发球！"
            })
            return
        
        # 获取玩家技能熟练度
        player_skills = room.players[username]["skills"]
        skill_level = player_skills.get(skill, 0)
        
        # 计算低质量球加成
        low_quality_bonus = 0
        if room.game_state["last_shot_quality"] == "low" and room.game_state["last_shot_value"]:
            low_quality_bonus = room.game_state["last_shot_value"] // 4
        
        # 投掷随机数
        base_roll = random.randint(1, 20)
        result = calculate_shot_result(base_roll, skill_level, low_quality_bonus)
        
        # 生成AI描述
        description = await generate_ai_description(skill, result, room.game_state)
        
        # 判断是否得分
        scored = False
        scorer = None
        
        # 如果是大成功且是杀球，直接得分
        if result["is_critical_success"] and skill == "杀球":
            scored = True
            scorer = username
        
        # 更新游戏状态
        room.game_state["last_shot_quality"] = result["quality"]
        room.game_state["last_shot_value"] = result["final_roll"]
        room.game_state["is_first_shot"] = False  # 第一球已打完
        room.game_state["rally_count"] = room.game_state.get("rally_count", 0) + 1
        
        shot_info = {
            "type": "shot_result",
            "player": username,
            "skill": skill,
            "message": message,
            "result": result,
            "description": description,
            "scored": scored,
            "scorer": scorer
        }
        
        # 如果得分，更新比分
        if scored:
            if username in [list(room.players.keys())[0]]:
                room.game_state["score_a"] += 1
            else:
                room.game_state["score_b"] += 1
            
            # 重置回合状态
            room.game_state["is_first_shot"] = True
            room.game_state["rally_count"] = 0
            room.game_state["last_shot_quality"] = None
            room.game_state["last_shot_value"] = None
            
            shot_info["game_state"] = room.game_state
            
            # 检查是否游戏结束（21分制，赛点时需领先2分）
            score_a = room.game_state["score_a"]
            score_b = room.game_state["score_b"]
            game_over = False
            
            # 至少21分且领先2分，或者达到30分
            if score_a >= 21 or score_b >= 21:
                if abs(score_a - score_b) >= 2 or score_a >= 30 or score_b >= 30:
                    game_over = True
            
            if game_over:
                room.game_state["status"] = "finished"
                shot_info["game_over"] = True
        
        await broadcast_to_room(room, shot_info)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

