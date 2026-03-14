# -*- coding: utf-8 -*-
"""
用户数据管理 - 持久化存储用户设置
"""
import os
import json
import threading
from typing import Dict, Any, Optional, List
from datetime import date, datetime

import config


class UserDataManager:
    """用户数据管理器"""
    
    DEFAULT_DATA = {
        "pet_name": "我的小宠物",
        "created_at": None,
        "total_usage_time": 0,
        "last_launch": None,
        "launch_count": 0,
        "messages_sent": 0,
        "emotions_sent": 0,
        # 专注系统数据
        "daily_focus_seconds": 0,
        "total_focus_seconds": 0,
        "focus_date": None,
        # 历史最高单次专注（用于皮肤等级解锁）
        "max_focus_seconds": 0,
        # 分类专注时长（累计）
        "english_focus_seconds": 0,
        "coding_focus_seconds": 0,
        # 存币系统
        "total_coins": 0,
        # 角色系统
        "current_character": "cat",
        "cheems_unlocked": False,
        # 皮肤系统
        "owned_skins": [],
        "today_skin": None,
    }
    
    def __init__(self, data_file: str = None):
        if data_file is None:
            self._data_file = os.path.join(config.get_app_path(), "userdata.json")
        else:
            self._data_file = data_file
        
        self._data: Dict[str, Any] = {}
        self._session_start: Optional[datetime] = None
        self._dirty = False
        self._save_lock = threading.Lock()
        self._load()
    
    def _load(self):
        """从文件加载数据"""
        if os.path.exists(self._data_file):
            try:
                with open(self._data_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self._data = {**self.DEFAULT_DATA, **loaded}
                
                today = str(date.today())
                if self._data.get("focus_date") != today:
                    self._data["daily_focus_seconds"] = 0
                    self._data["focus_date"] = today
                    self._dirty = True
                
                print(f"[用户数据] 已加载: {self._data_file}")
            except Exception as e:
                print(f"[用户数据] 加载失败: {e}")
                self._data = self.DEFAULT_DATA.copy()
        else:
            self._data = self.DEFAULT_DATA.copy()
            self._data["focus_date"] = str(date.today())
            print(f"[用户数据] 创建新数据文件")
    
    def save(self, force: bool = False):
        """保存数据到文件（异步，不阻塞UI线程）"""
        if not force and not self._dirty:
            return
        
        # 更新会话时间
        if self._session_start:
            session_time = (datetime.now() - self._session_start).total_seconds()
            self._data["total_usage_time"] += session_time
            self._session_start = datetime.now()
        
        self._dirty = False
        
        # 拷贝数据快照，在后台写入
        data_snapshot = json.dumps(self._data, ensure_ascii=False, indent=2)
        
        if force:
            # 强制保存（退出时）：同步写入确保不丢数据
            self._write_to_file(data_snapshot)
        else:
            # 常规保存：后台线程写入
            threading.Thread(
                target=self._write_to_file,
                args=(data_snapshot,),
                daemon=True
            ).start()
    
    def _write_to_file(self, data_str: str):
        """实际写入文件（线程安全）"""
        with self._save_lock:
            try:
                with open(self._data_file, 'w', encoding='utf-8') as f:
                    f.write(data_str)
                print(f"[用户数据] 已保存")
            except Exception as e:
                print(f"[用户数据] 保存失败: {e}")
    
    def start_session(self):
        """开始会话"""
        self._session_start = datetime.now()
        
        if self._data.get("created_at") is None:
            self._data["created_at"] = datetime.now().isoformat()
        
        self._data["last_launch"] = datetime.now().isoformat()
        self._data["launch_count"] = self._data.get("launch_count", 0) + 1
        
        self.save(force=True)
    
    def end_session(self):
        """结束会话"""
        self.save(force=True)
    
    def mark_dirty(self):
        """标记数据需要保存"""
        self._dirty = True
    
    # ==================== 基础属性 ====================
    
    @property
    def pet_name(self) -> str:
        return self._data.get("pet_name", self.DEFAULT_DATA["pet_name"])
    
    @pet_name.setter
    def pet_name(self, value: str):
        self._data["pet_name"] = value
        self._dirty = True
    
    @property
    def launch_count(self) -> int:
        return self._data.get("launch_count", 0)
    
    @property
    def total_usage_time(self) -> int:
        return self._data.get("total_usage_time", 0)
    
    @property
    def total_usage_time_formatted(self) -> str:
        seconds = self.total_usage_time
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if hours > 0:
            return f"{hours}小时{minutes}分钟"
        return f"{minutes}分钟"
    
    # ==================== 专注系统 ====================
    
    @property
    def daily_focus_seconds(self) -> int:
        return self._data.get("daily_focus_seconds", 0)
    
    @daily_focus_seconds.setter
    def daily_focus_seconds(self, value: int):
        self._data["daily_focus_seconds"] = value
        self._dirty = True
    
    @property
    def total_focus_seconds(self) -> int:
        return self._data.get("total_focus_seconds", 0)
    
    @total_focus_seconds.setter
    def total_focus_seconds(self, value: int):
        self._data["total_focus_seconds"] = value
        self._dirty = True
    
    @property
    def max_focus_seconds(self) -> int:
        """历史最高单次专注秒数"""
        return self._data.get("max_focus_seconds", 0)
    
    @max_focus_seconds.setter
    def max_focus_seconds(self, value: int):
        self._data["max_focus_seconds"] = value
        self._dirty = True
    
    def add_focus_time(self, seconds: int):
        """添加专注时间并增加存币"""
        self._data["daily_focus_seconds"] = self._data.get("daily_focus_seconds", 0) + seconds
        self._data["total_focus_seconds"] = self._data.get("total_focus_seconds", 0) + seconds
        self._data["total_coins"] = self._data.get("total_coins", 0) + seconds
        
        # 更新历史最高记录
        current_max = self._data.get("max_focus_seconds", 0)
        daily = self._data.get("daily_focus_seconds", 0)
        if daily > current_max:
            self._data["max_focus_seconds"] = daily
        
        self._dirty = True
    
    def get_daily_focus_formatted(self) -> str:
        """获取格式化的今日专注时间"""
        seconds = self.daily_focus_seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if hours > 0:
            return f"{hours}h{minutes}m"
        return f"{minutes}m"
    
    def get_max_focus_formatted(self) -> str:
        """获取格式化的历史最高专注时间"""
        seconds = self.max_focus_seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if hours > 0:
            return f"{hours}h{minutes}m"
        return f"{minutes}m"
    
    # ==================== 存币系统 ====================
    
    @property
    def total_coins(self) -> int:
        return self._data.get("total_coins", 0)
    
    @total_coins.setter
    def total_coins(self, value: int):
        self._data["total_coins"] = value
        self._dirty = True
    
    def spend_coins(self, amount: int) -> bool:
        """花费存币，返回是否成功"""
        if self._data.get("total_coins", 0) >= amount:
            self._data["total_coins"] -= amount
            self._dirty = True
            return True
        return False
    
    # ==================== 角色系统 ====================
    
    @property
    def current_character(self) -> str:
        return self._data.get("current_character", "cat")
    
    @current_character.setter
    def current_character(self, value: str):
        self._data["current_character"] = value
        self._dirty = True
    
    @property
    def cheems_unlocked(self) -> bool:
        return self._data.get("cheems_unlocked", False)
    
    @cheems_unlocked.setter
    def cheems_unlocked(self, value: bool):
        self._data["cheems_unlocked"] = value
        self._dirty = True
    
    def check_cheems_unlock(self) -> bool:
        """检查并更新cheems解锁状态"""
        if self.cheems_unlocked:
            return True
        max_minutes = self.max_focus_seconds // 60
        if max_minutes >= config.CHEEMS_UNLOCK_MINUTES:
            self.cheems_unlocked = True
            return True
        return False
    
    # ==================== 分类专注时长 ====================
    
    @property
    def english_focus_seconds(self) -> int:
        return self._data.get("english_focus_seconds", 0)
    
    @english_focus_seconds.setter
    def english_focus_seconds(self, value: int):
        self._data["english_focus_seconds"] = value
        self._dirty = True
    
    @property
    def coding_focus_seconds(self) -> int:
        return self._data.get("coding_focus_seconds", 0)
    
    @coding_focus_seconds.setter
    def coding_focus_seconds(self, value: int):
        self._data["coding_focus_seconds"] = value
        self._dirty = True
    
    def add_english_focus_time(self, seconds: int):
        """添加英语专注时间"""
        self._data["english_focus_seconds"] = self._data.get("english_focus_seconds", 0) + seconds
        self._dirty = True
    
    def add_coding_focus_time(self, seconds: int):
        """添加代码专注时间"""
        self._data["coding_focus_seconds"] = self._data.get("coding_focus_seconds", 0) + seconds
        self._dirty = True
    
    def get_english_focus_formatted(self) -> str:
        """获取格式化的英语累计专注时间"""
        seconds = self.english_focus_seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if hours > 0:
            return f"{hours}h{minutes}m"
        return f"{minutes}m"
    
    def get_coding_focus_formatted(self) -> str:
        """获取格式化的代码累计专注时间"""
        seconds = self.coding_focus_seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if hours > 0:
            return f"{hours}h{minutes}m"
        return f"{minutes}m"
    
    # ==================== 皮肤系统 ====================
    
    @property
    def owned_skins(self) -> List[str]:
        return self._data.get("owned_skins", [])
    
    @property
    def today_skin(self) -> Optional[str]:
        return self._data.get("today_skin")
    
    @today_skin.setter
    def today_skin(self, value: str):
        self._data["today_skin"] = value
        self._dirty = True
    
    def own_skin(self, skin_name: str) -> bool:
        """购买皮肤"""
        if skin_name not in self._data.get("owned_skins", []):
            if "owned_skins" not in self._data:
                self._data["owned_skins"] = []
            self._data["owned_skins"].append(skin_name)
            self._dirty = True
        return True
    
    def is_skin_owned(self, skin_name: str) -> bool:
        return skin_name in self._data.get("owned_skins", [])
    
    def is_skin_unlocked(self, skin_name: str, required_minutes: int) -> bool:
        """检查皮肤是否已解锁（等级要求）"""
        base = os.path.splitext(skin_name)[0]
        
        # lvEn 皮肤: 需要英语累计专注达标
        if base.startswith("lvEn"):
            en_minutes = self.english_focus_seconds // 60
            return en_minutes >= config.ENGLISH_SKIN_UNLOCK_MINUTES
        
        # lvpy 皮肤: 需要代码累计专注达标
        if base.startswith("lvpy"):
            py_minutes = self.coding_focus_seconds // 60
            return py_minutes >= config.CODING_SKIN_UNLOCK_MINUTES
        
        # 普通等级皮肤
        if required_minutes == 0:
            return True
        max_minutes = self.max_focus_seconds // 60
        return max_minutes >= required_minutes
    
    # ==================== 统计更新 ====================
    
    def increment_messages(self):
        self._data["messages_sent"] = self._data.get("messages_sent", 0) + 1
        self._dirty = True
    
    def increment_emotions(self):
        self._data["emotions_sent"] = self._data.get("emotions_sent", 0) + 1
        self._dirty = True
    
    # ==================== 通用接口 ====================
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)
    
    def set(self, key: str, value: Any):
        self._data[key] = value
        self._dirty = True
    
    def get_all_stats(self) -> Dict[str, Any]:
        return {
            "pet_name": self.pet_name,
            "launch_count": self.launch_count,
            "total_usage_time": self.total_usage_time_formatted,
            "messages_sent": self._data.get("messages_sent", 0),
            "emotions_sent": self._data.get("emotions_sent", 0),
            "daily_focus": self.get_daily_focus_formatted(),
            "max_focus": self.get_max_focus_formatted(),
            "english_focus": self.get_english_focus_formatted(),
            "coding_focus": self.get_coding_focus_formatted(),
            "total_coins": self.total_coins,
            "owned_skins": len(self.owned_skins),
            "current_character": self.current_character,
            "cheems_unlocked": self.cheems_unlocked,
            "created_at": self._data.get("created_at"),
            "last_launch": self._data.get("last_launch"),
        }