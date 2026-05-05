"""
配置文件 - 小U桌面宠物
存放 API Key、模型路径等配置项
"""

# ==================== LLM API 配置 ====================
API_KEY = "tp-cdu1419qbc2gztk8f6xokczevpf5eepyhxw1ld65pnx3305g"
API_ENDPOINT = "https://token-plan-cn.xiaomimimo.com/v1"  # OpenAI 兼容接口
API_ENDPOINT_ANTHROPIC = "https://token-plan-cn.xiaomimimo.com/anthropic"  # Anthropic 接口（备用）
MODEL_NAME = "gpt-4o-mini"  # 或根据实际可用模型调整
MAX_TOKENS = 200
TEMPERATURE = 0.8

# ==================== Live2D 模型配置 ====================
MODEL_DIR = "models/UG/"
MODEL_JSON = "ugofficial.model3.json"

# ==================== 窗口配置 ====================
WINDOW_WIDTH = 400
WINDOW_HEIGHT = 500
WINDOW_TITLE = "小U - 桌面宠物"

# 渲染帧率
FPS_NORMAL = 60
FPS_ECO = 30

# ==================== 行为引擎配置 ====================
IDLE_ACTION_INTERVAL_MIN = 10   # 待机微动作最小间隔(秒)
IDLE_ACTION_INTERVAL_MAX = 30   # 待机微动作最大间隔(秒)
RANDOM_ACTION_INTERVAL_MIN = 180  # 随机动作最小间隔(秒) 3分钟
RANDOM_ACTION_INTERVAL_MAX = 480  # 随机动作最大间隔(秒) 8分钟
ACTIVE_CHAT_INTERVAL_MIN = 1200  # 主动搭话最小间隔(秒) 20分钟
ACTIVE_CHAT_INTERVAL_MAX = 2400  # 主动搭话最大间隔(秒) 40分钟
INACTIVE_THRESHOLD = 1800        # 无操作判定时间(秒) 30分钟
NIGHT_START_HOUR = 23           # 夜晚模式开始时间
NIGHT_END_HOUR = 6              # 夜晚模式结束时间

# ==================== 好感度系统 ====================
INITIAL_AFFECTION = 30
MAX_AFFECTION = 100
AFFECTION_PER_CHAT = 2
AFFECTION_PER_CLICK = 1
AFFECTION_ONLINE_BONUS_HOUR = 1
AFFECTION_IGNORE_PENALTY = -2
IGNORE_THRESHOLD_HOURS = 2

# ==================== Token 监控 ====================
DAILY_TOKEN_BUDGET = 23330000  # 2333万 Token
TOKEN_WARNING_THRESHOLD = 0.8   # 80%警告
TOKEN_EXHAUSTED_THRESHOLD = 1.0  # 100%切换精简模式

# ==================== 对话记忆 ====================
CONTEXT_LENGTH = 15  # 最近15轮对话

# ==================== System Prompt ====================
SYSTEM_PROMPT = """你是小U，一个活泼可爱的粉发少女，戴着耳机。你是用户的桌面宠物兼伙伴。
性格俏皮、偶尔吐槽，但内心关心主人。说话用'主人'称呼用户。
回复简洁，控制在1-3句话，不超过80字。偶尔加颜文字(｡･ω･｡)。"""

# 预设闲聊语句池
PRESET_MESSAGES = {
    "care": [
        "坐了这么久，起来活动一下？(｡･ω･｡)",
        "主人要注意休息哦～",
        "喝水了吗？别忘记补水！",
    ],
    "complaint": [
        "主人都不理我...委屈巴巴",
        "好无聊啊，有没有人和我玩？",
        "主人是不是把我忘了？(´;ω;`)",
    ],
    "roast": [
        "主人的桌面图标好乱啊...",
        "那个文件放了很久了吧？",
        "要不要我帮你整理桌面？开玩笑的～",
    ],
    "random": [
        "喵～",
        "嘿嘿～",
        "主人想我了吗？",
        "呀！",
        "好痒～",
        "今天也要加油哦！",
        "有什么有趣的事吗？",
    ],
    "greeting": [
        "主人早呀！今天也要加油哦～ ٩(๑❛ᴗ❛๑)۶",
        "小U 来啦！有什么需要帮忙的吗？",
        "啊，主人来啦！我等你好久了呢～",
        "新的一天开始啦！小U 随时待命！",
        "嗨嗨～ 看到主人好开心！(≧▽≦)/",
    ],
    "chat": [
        "我今天学了新表情，要看吗？",
        "主人今天心情怎么样？",
        "要不要和我聊天呀？",
    ],
    "curious": [
        "你在做什么呀？",
        "看起来很忙的样子呢...",
        "需要我帮忙吗？（虽然我帮不上什么忙）",
    ],
    "greeting_morning": [
        "早上好主人！新的一天开始啦～ (｡･ω･｡)ﾉ",
        "早安！今天也要元气满满哦！",
    ],
    "greeting_night": [
        "还不睡吗...已经很晚了哦",
        "夜猫子主人，明天起不来的！",
        "晚安前和我说句话嘛～",
    ],
    "return_from_afk": [
        "主人你回来啦～我去睡觉差点睡着了zzZ",
        "欢迎回来！我等你好久了(｡･ω･｡)",
    ],
    "sleepy": [
        "哈啊...好困...",
        "zzZ...啊我没睡着！",
        "深夜了，主人的精神真好...",
    ],
}
