# -*- coding: utf-8 -*-
"""
专注管理器 - 管理专注计时和状态检测（含后台线程检测）
"""
import os
import re
import time
import threading
from typing import Optional, Tuple
from datetime import date

from PyQt5.QtCore import QThread, pyqtSignal

import config

# 检测可选模块
try:
    import win32gui
    import win32process
    import psutil
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    print("警告: 未安装 pywin32/psutil，窗口检测功能不可用")

# 预编译正则表达式
BLACKLIST_RE = re.compile(
    '|'.join(re.escape(kw) for kw in config.BLACKLIST_KEYWORDS), re.IGNORECASE
)
BROWSER_RE = re.compile(
    '|'.join(re.escape(kw) for kw in config.BROWSER_APPS), re.IGNORECASE
)
STUDY_RE = re.compile(
    '|'.join(re.escape(kw) for kw in config.STUDY_APPS), re.IGNORECASE
)
ENTERTAINMENT_RE = re.compile(
    '|'.join(re.escape(kw) for kw in config.ENTERTAINMENT_APPS), re.IGNORECASE
)
STUDY_EXT_RE = re.compile(
    '|'.join(re.escape(ext) for ext in config.STUDY_EXTENSIONS), re.IGNORECASE
)
ENGLISH_STUDY_RE = re.compile(
    '|'.join(re.escape(kw) for kw in config.ENGLISH_STUDY_APPS), re.IGNORECASE
)
ENGLISH_WEB_RE = re.compile(
    '|'.join(re.escape(kw) for kw in config.ENGLISH_WEB_KEYWORDS), re.IGNORECASE
)
CODING_STUDY_RE = re.compile(
    '|'.join(re.escape(kw) for kw in config.CODING_STUDY_APPS), re.IGNORECASE
)
CODING_EXT_RE = re.compile(
    '|'.join(re.escape(ext) for ext in config.CODING_EXTENSIONS), re.IGNORECASE
)


class FocusManager:
    """专注状态管理器"""
    
    # 状态常量
    STATE_NEUTRAL = "neutral"
    STATE_STUDY = "study"
    STATE_ENTERTAINMENT = "entertainment"
    
    # 学习类型常量
    STUDY_TYPE_ENGLISH = "english"
    STUDY_TYPE_CODING = "coding"
    STUDY_TYPE_GENERAL = "general"
    
    def __init__(self):
        # 专注计时相关
        self._study_start_time: Optional[float] = None
        self._is_studying = False
        self._focus_seconds = 0
        self._is_idle_timeout = False
        
        # 玩耍计时相关
        self._play_start_time: Optional[float] = None
        self._is_playing = False
        self._play_seconds = 0
        
        # 学习类型追踪
        self._current_study_type: str = self.STUDY_TYPE_GENERAL
        
        # 窗口变化追踪
        self._last_window_change_time = time.time()
        self._last_window_info = ""
        
        # 性能优化缓存
        self._process_cache = {}  # {pid: (process_name, timestamp)}
        self._my_pid = os.getpid()
        self._last_classified_info = ""
        self._last_is_study = False
        self._last_is_entertainment = False
        self._last_study_type = self.STUDY_TYPE_GENERAL
    
    @property
    def focus_seconds(self) -> int:
        return self._focus_seconds
    
    @property
    def play_seconds(self) -> int:
        return self._play_seconds
    
    @property
    def is_studying(self) -> bool:
        return self._is_studying
    
    @property
    def is_playing(self) -> bool:
        return self._is_playing
    
    @property
    def current_study_type(self) -> str:
        """当前学习类型: english, coding, general"""
        return self._current_study_type
    
    @property
    def current_state(self) -> str:
        if self._is_studying:
            return self.STATE_STUDY
        elif self._is_playing:
            return self.STATE_ENTERTAINMENT
        return self.STATE_NEUTRAL
    
    def get_focus_time_text(self) -> str:
        """获取格式化的专注时间文本"""
        minutes = self._focus_seconds // 60
        seconds = self._focus_seconds % 60
        
        if minutes >= 60:
            hours = minutes // 60
            minutes = minutes % 60
            return f"专注 {hours}h{minutes}m"
        return f"专注 {minutes}m{seconds}s"
    
    def get_play_time_text(self) -> str:
        """获取格式化的玩耍时间文本"""
        minutes = self._play_seconds // 60
        seconds = self._play_seconds % 60
        
        if minutes >= 60:
            hours = minutes // 60
            minutes = minutes % 60
            return f"玩耍 {hours}h{minutes}m"
        return f"玩耍 {minutes}m{seconds}s"
    
    def check_active_window(self) -> Tuple[str, dict]:
        """
        检测当前活动窗口并更新状态
        
        Returns:
            (状态, 状态信息字典)
        """
        if not HAS_WIN32:
            return self.STATE_NEUTRAL, {}
        
        try:
            hwnd = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process_name = self._get_process_name(pid)
            
            # 焦点在自己身上时，只更新计时，不切换状态
            if pid == self._my_pid:
                self._update_current_timer()
                return self.current_state, {"timer_only": True}
            
            current_window_info = f"{process_name}:{window_title}"
            current_time = time.time()
            
            # 检测窗口是否变化
            window_changed = (current_window_info != self._last_window_info)
            if window_changed:
                self._last_window_info = current_window_info
                self._last_window_change_time = current_time
                self._is_idle_timeout = False
            
            # 缓存分类结果
            if window_changed:
                self._last_is_study = self._is_study_app(window_title, process_name)
                self._last_is_entertainment = self._is_entertainment_app(window_title, process_name)
                if self._last_is_study:
                    self._last_study_type = self._classify_study_type(window_title, process_name)
                else:
                    self._last_study_type = self.STUDY_TYPE_GENERAL
            
            is_study = self._last_is_study
            is_entertainment = self._last_is_entertainment
            
            if is_study:
                return self._handle_study_state(current_time)
            elif is_entertainment:
                return self._handle_entertainment_state(current_time, window_title)
            else:
                return self._handle_neutral_state()
                
        except Exception as e:
            print(f"[窗口检测错误] {e}")
            return self.current_state, {}
    
    def _get_process_name(self, pid: int) -> str:
        """获取进程名（带缓存）"""
        current_time = time.time()
        
        if pid in self._process_cache:
            cached_name, cache_time = self._process_cache[pid]
            if current_time - cache_time < config.CACHE_EXPIRE:
                return cached_name
        
        try:
            process = psutil.Process(pid)
            name = process.name().lower()
            self._process_cache[pid] = (name, current_time)
            return name
        except Exception:
            return ""
    
    def _is_study_app(self, window_title: str, process_name: str) -> bool:
        """判断是否是学习软件"""
        title_lower = window_title.lower()
        process_lower = process_name.lower()
        
        # 检查黑名单
        if BLACKLIST_RE.search(title_lower):
            return False
        
        # 检查是否是浏览器
        if BROWSER_RE.search(process_lower):
            return True
        
        # 检查学习软件关键词
        if STUDY_RE.search(title_lower) or STUDY_RE.search(process_lower):
            return True
        
        # 检测文件扩展名
        if STUDY_EXT_RE.search(title_lower):
            return True
        
        return False
    
    def _is_entertainment_app(self, window_title: str, process_name: str) -> bool:
        """判断是否是娱乐软件"""
        title_lower = window_title.lower()
        process_lower = process_name.lower()
        
        # 检查是否是娱乐软件进程
        if ENTERTAINMENT_RE.search(process_lower):
            return True
        
        # 检查是否是浏览器打开黑名单网站
        if BROWSER_RE.search(process_lower):
            return bool(BLACKLIST_RE.search(title_lower))
        
        # 检查窗口标题是否包含黑名单关键词
        if BLACKLIST_RE.search(title_lower):
            return True
        
        return False
    
    def _classify_study_type(self, window_title: str, process_name: str) -> str:
        """分类学习类型: english, coding, general"""
        title_lower = window_title.lower()
        process_lower = process_name.lower()
        
        # 检查英语学习软件
        if ENGLISH_STUDY_RE.search(title_lower) or ENGLISH_STUDY_RE.search(process_lower):
            return self.STUDY_TYPE_ENGLISH
        
        # 检查浏览器中的英语学习内容
        if BROWSER_RE.search(process_lower) and ENGLISH_WEB_RE.search(title_lower):
            return self.STUDY_TYPE_ENGLISH
        
        # 检查编程软件
        if CODING_STUDY_RE.search(process_lower):
            return self.STUDY_TYPE_CODING
        
        # 检查编程相关文件扩展名
        if CODING_EXT_RE.search(title_lower):
            return self.STUDY_TYPE_CODING
        
        return self.STUDY_TYPE_GENERAL
    
    def _update_current_timer(self):
        """焦点在自身时，仅更新当前模式的计时"""
        current_time = time.time()
        
        if self._is_studying and self._study_start_time and not self._is_idle_timeout:
            self._focus_seconds = int(current_time - self._study_start_time)
        elif self._is_playing and self._play_start_time:
            self._play_seconds = int(current_time - self._play_start_time)
    
    def _handle_study_state(self, current_time: float) -> Tuple[str, dict]:
        """处理学习软件状态"""
        # 如果之前在玩耍，重置
        if self._is_playing:
            self._reset_play()
        
        if not self._is_studying:
            self._is_studying = True
            self._study_start_time = current_time
            self._focus_seconds = 0
            self._is_idle_timeout = False
        
        # 更新学习类型
        self._current_study_type = self._last_study_type
        
        # 计算专注时长
        idle_duration = current_time - self._last_window_change_time
        if idle_duration >= config.M_IDLE_TIMEOUT * 60:
            if not self._is_idle_timeout:
                self._is_idle_timeout = True
                self._focus_seconds = int(
                    current_time - self._study_start_time - idle_duration + config.M_IDLE_TIMEOUT * 60
                )
        else:
            self._focus_seconds = int(current_time - self._study_start_time)
        
        return self.STATE_STUDY, {
            "focus_seconds": self._focus_seconds,
            "time_text": self.get_focus_time_text(),
            "study_type": self._current_study_type
        }
    
    def _handle_entertainment_state(self, current_time: float, window_title: str) -> Tuple[str, dict]:
        """处理娱乐软件状态"""
        # 如果之前在学习，重置
        if self._is_studying:
            self._reset_focus()
        
        if not self._is_playing:
            self._is_playing = True
            self._play_start_time = current_time
            self._play_seconds = 0
        
        self._play_seconds = int(current_time - self._play_start_time)
        
        return self.STATE_ENTERTAINMENT, {
            "play_seconds": self._play_seconds,
            "time_text": self.get_play_time_text()
        }
    
    def _handle_neutral_state(self) -> Tuple[str, dict]:
        """处理中性状态"""
        if self._is_studying:
            self._reset_focus()
        if self._is_playing:
            self._reset_play()
        
        return self.STATE_NEUTRAL, {}
    
    def _reset_focus(self):
        """重置专注状态"""
        self._is_studying = False
        self._study_start_time = None
        self._focus_seconds = 0
        self._is_idle_timeout = False
        self._current_study_type = self.STUDY_TYPE_GENERAL
    
    def _reset_play(self):
        """重置玩耍状态"""
        self._is_playing = False
        self._play_start_time = None
        self._play_seconds = 0
    
    def get_new_focus_seconds(self) -> int:
        """
        获取自上次调用以来新增的专注秒数（用于计算存币）
        并重置计数
        """
        new_seconds = self._focus_seconds
        self._focus_seconds = 0
        if self._study_start_time:
            self._study_start_time = time.time()
        return new_seconds
    
    def reset_daily(self):
        """重置每日数据"""
        self._reset_focus()
        self._reset_play()


class FocusWorker(QThread):
    """后台线程执行窗口检测，避免阻塞UI"""
    
    # 信号: (state_str, info_dict)
    focus_checked = pyqtSignal(str, dict)
    
    def __init__(self, focus_manager: FocusManager, interval_ms: int = 5000, parent=None):
        super().__init__(parent)
        self._focus_manager = focus_manager
        self._interval = interval_ms / 1000.0  # 转为秒
        self._running = False
    
    def run(self):
        """线程主循环"""
        self._running = True
        while self._running:
            try:
                state, info = self._focus_manager.check_active_window()
                self.focus_checked.emit(state, info)
            except Exception as e:
                print(f"[FocusWorker] 检测错误: {e}")
            
            # 使用可中断的 sleep
            deadline = time.time() + self._interval
            while self._running and time.time() < deadline:
                time.sleep(0.2)
    
    def stop(self):
        """停止工作线程"""
        self._running = False
        self.wait(3000)  # 最多等3秒