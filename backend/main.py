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
        self.players: Dict[str, dict] = {}  # 参赛玩家
        self.spectators: Dict[str, dict] = {}  # 观众
        self.websockets: Dict[str, WebSocket] = {}  # 所有连接（包括观众）
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
            "rally_count": 0,  # 回合计数
            "current_team": None,  # 当前该哪个队伍击球 ("A" or "B")
            "last_player": None,  # 上一个击球的玩家
            "team_a": [],  # 队伍A的玩家
            "team_b": []  # 队伍B的玩家
        }
    
    def get_player_team(self, username: str) -> str:
        """获取玩家所属队伍"""
        if username in self.game_state["team_a"]:
            return "A"
        elif username in self.game_state["team_b"]:
            return "B"
        return None

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

async def generate_ai_description(skill: str, result: dict, game_state: dict, player_message: str = "", scored: bool = False, score_reason: str = None) -> str:
    """
    调用AI生成击球描述
    :param skill: 使用的技能
    :param result: 击球结果
    :param game_state: 游戏状态
    :param player_message: 玩家输入的对话内容
    :param scored: 是否得分
    :param score_reason: 得分原因
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
        
        # 构建提示词
        player_intent = f"\n玩家意图：{player_message}" if player_message.strip() else ""
        score_info = f"\n【得分情况】：是，原因：{score_reason}" if scored else "\n【得分情况】：否，回合继续"
        
        prompt = f"""你是一个顶级的羽毛球比赛解说员，拥有专业的解说素养和幽默风趣的风格。

【比赛情况】
技术动作：{skill}
实际效果：{quality_desc}
数值：{result['final_roll']}/20分（基础掷骰：{result['base_roll']}/20）
当前比分：{score_a}:{score_b}{player_intent}{score_info}

【解说规则】
1. 必须客观反映实际效果和得分情况：
   - 如果得分，务必说明得分（如"得分了！"、"拿下这一分！"、"这球得分！"）
   - 大失败（1-2分）：严重失误，如"球挂网了！"、"直接出界！"、"根本没碰到球！对方得分！"
   - 低质量（3-8分）：较差表现，如"回球无力"、"质量堪忧"、"给了对手好机会"
   - 普通（9-14分）：中规中矩，如"稳健处理"、"常规回球"、"保持节奏"
   - 高质量（15-19分）：精彩表现，如"这球质量很高！"、"极具威胁！"、"对方难以招架！得分！"
   - 大成功（20分）：完美表现，如"神仙球！直接得分！"、"无懈可击！"、"教科书般的一击！拿下这分！"

2. 如果玩家有输入意图描述：
   - 当意图与实际效果一致时：赞美玩家，如"正如他所想，完美执行！"
   - 当意图与实际效果不符时：制造戏剧性，如"想法很好，可惜..."、"事与愿违！"
   - 融入玩家的想法到解说中，让解说更生动

3. 专业解说要素：
   - 用词精准，符合羽毛球术语
   - 制造画面感，让人身临其境
   - 如果是关键分（19分以上），增加紧张感和激情
   - 可适当幽默但不失专业

4. 字数：20-30字，简洁有力

【示例】
- 大失败+玩家说"全力一击"："想要全力扣杀，可惜球直接挂网了！机会浪费！"
- 高质量+玩家说"刁钻角度"："刁钻的角度！这球落点精准，对手疲于奔命！"
- 低质量+没有玩家输入："回球质量不高，软绵绵的，给对手创造了进攻机会"

只返回解说词，不要其他内容。"""

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
        quality_base = {
            "critical_fail": "严重失误！球直接下网",
            "low": "回球质量不佳，对方机会来了",
            "normal": "稳健回击，保持节奏",
            "high": "漂亮的一球！很有威胁",
            "critical_success": "完美击球！无懈可击！"
        }
        base_desc = quality_base.get(result['quality'], f"{skill}完成")
        
        # 添加得分信息
        if scored:
            base_desc += f" 得分！({score_reason})"
        
        # 如果有玩家输入，尝试结合
        if player_message.strip():
            if result['quality'] in ['high', 'critical_success']:
                return f"{player_message}！{base_desc}"
            else:
                return f"想{player_message}，可惜{base_desc}"
        
        return base_desc


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
    
    # 判断是否加入为观众
    is_spectator = False
    max_players = 2 if room.mode == "2p" else 4
    
    if room.game_state["status"] == "playing":
        # 游戏已开始，加入观众席
        is_spectator = True
        room.spectators[username] = player_profile
        room.websockets[username] = websocket
        
        await broadcast_to_room(room, {
            "type": "spectator_joined",
            "username": username,
            "players": list(room.players.keys()),
            "spectators": list(room.spectators.keys())
        })
    elif len(room.players) >= max_players:
        # 房间已满，加入观众席
        is_spectator = True
        room.spectators[username] = player_profile
        room.websockets[username] = websocket
        
        await broadcast_to_room(room, {
            "type": "spectator_joined",
            "username": username,
            "players": list(room.players.keys()),
            "spectators": list(room.spectators.keys())
        })
    else:
        # 加入为玩家
        room.players[username] = player_profile
        room.websockets[username] = websocket
        
        await broadcast_to_room(room, {
            "type": "player_joined",
            "username": username,
            "players": list(room.players.keys()),
            "spectators": list(room.spectators.keys()),
            "player_count": len(room.players)
        })
    
    try:
        while True:
            data = await websocket.receive_json()
            await handle_game_action(room, username, data, is_spectator)
    except WebSocketDisconnect:
        # 移除玩家或观众
        if username in room.players:
            del room.players[username]
        if username in room.spectators:
            del room.spectators[username]
        if username in room.websockets:
            del room.websockets[username]
            
        await broadcast_to_room(room, {
            "type": "player_left" if not is_spectator else "spectator_left",
            "username": username,
            "players": list(room.players.keys()),
            "spectators": list(room.spectators.keys())
        })

async def broadcast_to_room(room: GameRoom, message: dict):
    """向房间内所有玩家广播消息"""
    for ws in room.websockets.values():
        try:
            await ws.send_json(message)
        except:
            pass

async def handle_game_action(room: GameRoom, username: str, data: dict, is_spectator: bool = False):
    """处理游戏动作"""
    action_type = data.get("type")
    
    # 聊天消息，所有人都可以发送
    if action_type == "chat":
        chat_message = data.get("message", "").strip()
        if chat_message:
            await broadcast_to_room(room, {
                "type": "chat_message",
                "username": username,
                "message": chat_message,
                "is_spectator": is_spectator,
                "timestamp": datetime.now().isoformat()
            })
        return
    
    # 观众不能执行游戏动作
    if is_spectator and action_type in ["start_game", "restart_game", "shot"]:
        await room.websockets[username].send_json({
            "type": "error",
            "message": "观众不能参与游戏操作"
        })
        return
    
    if action_type == "start_game" or action_type == "restart_game":
        # 开始游戏或重新开始
        player_list = list(room.players.keys())
        
        # 分配队伍
        if room.mode == "2p":
            # 单打：一人一队
            room.game_state["team_a"] = [player_list[0]] if len(player_list) > 0 else []
            room.game_state["team_b"] = [player_list[1]] if len(player_list) > 1 else []
        else:
            # 双打：前两人A队，后两人B队
            room.game_state["team_a"] = player_list[:2]
            room.game_state["team_b"] = player_list[2:4] if len(player_list) > 2 else []
        
        # 随机决定哪队先发球
        first_team = random.choice(["A", "B"])
        room.game_state["current_team"] = first_team
        
        # 从先发球队伍中随机选一个人发球
        if first_team == "A" and room.game_state["team_a"]:
            room.game_state["current_server"] = random.choice(room.game_state["team_a"])
        elif room.game_state["team_b"]:
            room.game_state["current_server"] = random.choice(room.game_state["team_b"])
        
        room.game_state["status"] = "playing"
        room.game_state["score_a"] = 0
        room.game_state["score_b"] = 0
        room.game_state["last_shot_quality"] = None
        room.game_state["last_shot_value"] = None
        room.game_state["is_first_shot"] = True
        room.game_state["rally_count"] = 0
        room.game_state["rally_history"] = []
        room.game_state["last_player"] = None
        
        await broadcast_to_room(room, {
            "type": "game_started" if action_type == "start_game" else "game_restarted",
            "game_state": room.game_state
        })
    
    elif action_type == "shot":
        # 玩家击球
        skill = data.get("skill")
        message = data.get("message", "")
        
        # 获取玩家所属队伍
        player_team = room.get_player_team(username)
        if not player_team:
            await room.websockets[username].send_json({
                "type": "error",
                "message": "您不在任何队伍中"
            })
            return
        
        # 检查是否轮到该队伍击球
        if room.game_state["current_team"] and room.game_state["current_team"] != player_team:
            await room.websockets[username].send_json({
                "type": "error",
                "message": f"现在是队伍{room.game_state['current_team']}的回合，请等待！"
            })
            return
        
        # 检查是否同队连续击球（双打情况下，同队只能一人击一次）
        if room.game_state["last_player"] == username:
            await room.websockets[username].send_json({
                "type": "error",
                "message": "您刚刚已经击球，不能连续击球！"
            })
            return
        
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
        
        # 判断是否得分（基于击球质量和对方能否接住）
        scored = False
        scorer = None
        score_reason = None
        
        # 1. 自己大失败，直接失分（球下网、出界等）
        if result["is_critical_fail"] or result["final_roll"] <= 2:
            scored = True
            # 失分的是击球方的对方
            opponent_team = "B" if player_team == "A" else "A"
            # 找到对方队伍的一个玩家作为得分者
            opponent_players = room.game_state["team_b"] if opponent_team == "B" else room.game_state["team_a"]
            if opponent_players:
                scorer = opponent_players[0]  # 简化处理，记为对方队伍得分
            score_reason = "对方失误"
        
        # 2. 如果是第一球之后，判断对方是否能接住这一球
        elif not room.game_state.get("is_first_shot", True):
            # 模拟对方接球（使用对方队伍的平均技能水平）
            opponent_team = "B" if player_team == "A" else "A"
            opponent_players = room.game_state["team_b"] if opponent_team == "B" else room.game_state["team_a"]
            
            if opponent_players:
                # 计算对方队伍平均技能水平（简化处理，使用接发球技能）
                avg_skill = 0
                for opp in opponent_players:
                    if opp in room.players:
                        opp_skills = room.players[opp]["skills"]
                        # 根据当前技能类型选择对应的防守技能
                        if skill == "杀球":
                            avg_skill += opp_skills.get("挑球", 0)
                        elif skill == "吊球":
                            avg_skill += opp_skills.get("放网", 0)
                        else:
                            avg_skill += opp_skills.get("接发球", 0)
                avg_skill = avg_skill // len(opponent_players)
                
                # 对方尝试接球
                defense_roll = random.randint(1, 20)
                defense_result = calculate_shot_result(defense_roll, avg_skill, 0)
                
                # 判断能否接住
                if not can_receive_shot(defense_result, result["quality"], result["final_roll"]):
                    scored = True
                    scorer = username
                    score_reason = "对方无法回击"
        
        # 3. 大成功的杀球，依然是必杀
        if result["is_critical_success"] and skill == "杀球":
            scored = True
            scorer = username
            score_reason = "完美杀球"
        
        # 生成AI描述（结合玩家输入的对话和得分情况）
        description = await generate_ai_description(skill, result, room.game_state, message, scored, score_reason)
        
        # 更新游戏状态
        room.game_state["last_shot_quality"] = result["quality"]
        room.game_state["last_shot_value"] = result["final_roll"]
        room.game_state["is_first_shot"] = False  # 第一球已打完
        room.game_state["rally_count"] = room.game_state.get("rally_count", 0) + 1
        room.game_state["last_player"] = username
        
        # 切换队伍（下一球由对方击球）
        player_team = room.get_player_team(username)
        room.game_state["current_team"] = "B" if player_team == "A" else "A"
        
        shot_info = {
            "type": "shot_result",
            "player": username,
            "skill": skill,
            "message": message,
            "result": result,
            "description": description,
            "scored": scored,
            "scorer": scorer,
            "score_reason": score_reason,
            "game_state": room.game_state  # 每次击球都发送更新后的状态
        }
        
        # 如果得分，更新比分
        if scored:
            scorer_team = room.get_player_team(username)
            if scorer_team == "A":
                room.game_state["score_a"] += 1
            else:
                room.game_state["score_b"] += 1
            
            # 重置回合状态，得分方发球
            room.game_state["is_first_shot"] = True
            room.game_state["rally_count"] = 0
            room.game_state["last_shot_quality"] = None
            room.game_state["last_shot_value"] = None
            room.game_state["last_player"] = None
            room.game_state["current_team"] = scorer_team  # 得分方发球
            
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

