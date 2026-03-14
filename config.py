# config.py

import os
import sys

# ==================== 宠物设置 ====================
MAX_PET_WIDTH = 300
MAX_PET_HEIGHT = 300
DEFAULT_OFFSET_X = 200
DEFAULT_OFFSET_Y = 80

# ==================== 迷你宠物设置 ====================
MINI_PET_SCALE = 3
MAX_MINI_PETS_DISPLAY = 3
MINI_PET_SPACING = 5

# ==================== 动画资源 ====================
ANIMATIONS_DIR = "resources/animations"
ANIMATION_IDLE = "idle"

# ==================== 网络配置 ====================
NETWORK_PORT = 9527
DISCOVERY_PORT = 9528
DISCOVERY_INTERVAL = 3.0
HEARTBEAT_INTERVAL = 10.0
PEER_TIMEOUT_MULTIPLIER = 3

# ==================== 消息类型 ====================
MSG_TYPE_DISCOVERY = "discovery"
MSG_TYPE_HEARTBEAT = "heartbeat"
MSG_TYPE_EMOTION = "emotion"
MSG_TYPE_MESSAGE = "message"
MSG_TYPE_EXIT = "exit"
MSG_TYPE_STATUS = "status"
MSG_TYPE_ANIMATION = "animation"
MSG_TYPE_FOCUS_STATE = "focus_state"

# ==================== 显示时间配置 ====================
EMOTION_DISPLAY_DURATION = 3000
MESSAGE_DISPLAY_DURATION = 5000
MESSAGE_MAX_LENGTH = 30

# ==================== 表情映射 ====================
EMOTION_EMOJI = {
    "happy": "😊",
    "sad": "😢",
    "love": "❤️",
    "angry": "😠",
    "surprise": "😲",
    "gift": "🎁",
    "stand": "😐"
}

EMOTION_NAMES = {
    "happy": "开心 😊",
    "sad": "难过 😢",
    "love": "喜欢 ❤️",
    "angry": "生气 😠",
    "surprise": "惊讶 😲",
    "gift": "礼物 🎁",
    "stand": "普通 😐"
}

# ==================== 专注计时配置 ====================
M_IDLE_TIMEOUT = 1  # 无操作超时时间（分钟）
FOCUS_TRIGGER_SECONDS = 0  # 立即切换
PLAY_TRIGGER_SECONDS = 0   # 立即切换
SAVE_INTERVAL = 30  # 数据保存间隔（秒）
CACHE_EXPIRE = 60  # 进程名缓存过期时间（秒）
MONITOR_INTERVAL = 5000  # 窗口检测间隔（毫秒）

# ==================== 皮肤系统配置 ====================
SKINS_DIR = "resources/skins"
SKIN_PRICE = 25

# ==================== 角色系统配置 ====================
DEFAULT_CHARACTER = "cat"
AVAILABLE_CHARACTERS = ["cat", "cheems"]
CHEEMS_UNLOCK_MINUTES = 10  # 最高单次专注达到10分钟解锁cheems

# ==================== 分类专注时长解锁配置 ====================
ENGLISH_SKIN_UNLOCK_MINUTES = 10  # 英语累计专注10分钟解锁lvEn皮肤
CODING_SKIN_UNLOCK_MINUTES = 10   # 代码累计专注10分钟解锁lvpy皮肤

# ==================== 大语言模型API配置 ====================
LLM_API_KEY = "sk-qwziqsgqrgbcfoejvybfubtmvtflkagolfaimtwzzmzdoddl"
LLM_API_URL = "https://api.siliconflow.cn/v1/chat/completions"
LLM_MODEL = "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B"

# ==================== 应用分类配置 ====================
# 学习软件关键词
STUDY_APPS = {
    'code', 'vscode', 'pycharm', 'idea', 'eclipse', 'sublime', 'atom', 'vim', 'nvim',
    'visual studio', 'devenv', 'idle', 'jupyter', 'spyder', 'android studio',
    'winword', 'excel', 'powerpnt', 'word', 'wps', 'et', 'wpp',
    'acrobat', 'acrord32', 'foxit', 'sumatrapdf', 'pdf',
    '墨墨', '百词斩', '扇贝', '不背单词', 'anki', '欧路词典', '有道',
    'notion', 'obsidian', 'typora', 'markdown', 'onenote', 'evernote',
}

# 英语学习软件关键词
ENGLISH_STUDY_APPS = {
    '墨墨', '百词斩', '扇贝', '不背单词', 'anki', '欧路词典', '有道',
}

# 英语学习网页关键词（浏览器标题匹配）
ENGLISH_WEB_KEYWORDS = {
    '单词', 'vocabulary', 'english', '英语', 'duolingo', 'quizlet',
    '背单词', '词汇', '四级', '六级', 'ielts', 'toefl', 'gre',
}

# 编程学习软件关键词
CODING_STUDY_APPS = {
    'code', 'vscode', 'pycharm', 'idea', 'eclipse', 'sublime', 'atom', 'vim', 'nvim',
    'visual studio', 'devenv', 'idle', 'jupyter', 'spyder', 'android studio',
}

# 编程相关文件扩展名
CODING_EXTENSIONS = [
    '.py', '.java', '.cpp', '.c', '.js', '.ts', '.html', '.css',
    '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala',
]

# 浏览器进程名
BROWSER_APPS = {
    'chrome', 'msedge', 'firefox', 'opera', 'brave', 'vivaldi', 'safari',
    'chromium', '360se', 'qqbrowser', 'sogouexplorer', 'edge',
}

# 黑名单关键词
BLACKLIST_KEYWORDS = {
    'bilibili', 'b站', '哔哩哔哩', 'youtube', '优酷', '爱奇艺', '腾讯视频', '芒果tv',
    '抖音', '快手', 'tiktok', 'netflix', 'disney',
    '微博', 'weibo', '小红书', '豆瓣', 'twitter', 'facebook', 'instagram',
    'steam', '游戏', 'game', '英雄联盟', '王者荣耀', '原神', '4399',
    '淘宝', '天猫', '京东', '拼多多', '闲鱼', '得物',
    'qq空间', 'discord', 'telegram',
    '今日头条', '网易新闻', '腾讯新闻',
}

# 娱乐软件进程名
ENTERTAINMENT_APPS = {
    'wechat', 'weixin', 'qq', 'tim', 'telegram', 'discord', 'slack',
    'dingtalk', 'feishu', 'lark',
    'steam', 'steamwebhelper', 'wegame', 'epicgameslauncher', 'origin',
    'uplay', 'battlenet', 'gog',
    'leagueclient', 'league of legends', 'tgp', 'dnf', 'crossfire',
    'pubg', 'csgo', 'cs2', 'valorant', 'genshinimpact', 'yuanshen',
    'minecraft', 'javaw',
    'potplayer', 'vlc', 'mpc-hc', 'kmplayer', 'qqmusic', 'cloudmusic',
    'neteasemusic', 'kugou', 'kuwo', 'spotify',
    'obs', 'bilibililive', 'douyuex', 'huya',
}

# 学习相关文件扩展名
STUDY_EXTENSIONS = [
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.md', '.py', '.java', '.cpp', '.c', '.js', '.html', '.css'
]

# ==================== 路径工具 ====================
def get_base_path() -> str:
    """获取资源根目录（打包后指向 _internal/，开发时指向项目根）"""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def get_app_path() -> str:
    """获取应用目录（打包后指向 exe 所在目录，开发时指向项目根）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_resource_path(*parts: str) -> str:
    """获取资源文件路径"""
    return os.path.join(get_base_path(), *parts)
