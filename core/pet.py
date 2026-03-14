# -*- coding: utf-8 -*-
"""
桌面宠物核心类 - 完整版（含过渡动画、复习提纲功能）
"""
import os
import uuid
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import QWidget, QLabel, QApplication, QPushButton
from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtGui import QCursor, QFont, QPixmap

from .mood_manager import MoodManager
from .mini_pet import MiniPetContainer
from .focus_manager import FocusManager, FocusWorker
from network.manager import NetworkManager
from ui.menu import ContextMenu
from ui.notifications import NotificationManager
from ui.shop_dialog import ShopDialog, find_chinese_font
from utils.helpers import get_local_ip, check_module_available
from utils.userdata import UserDataManager
import config

HAS_WIN32 = check_module_available('win32gui')


class DesktopPet(QWidget):
    """桌面宠物主类"""
    
    TRANSITION_INTERVAL = 200
    
    def __init__(self, pet_name: str = "我的桌宠", user_data: UserDataManager = None):
        super().__init__()
        
        self._pet_name = pet_name
        self._pet_id = str(uuid.uuid4())[:8]
        self._local_ip = get_local_ip()
        
        self._user_data = user_data
        self._cn_font = find_chinese_font()
        
        self._mood_manager = MoodManager()
        self._notification_manager = NotificationManager(self)
        self._network_manager: Optional[NetworkManager] = None
        self._focus_manager = FocusManager()
        
        self._mini_pet_container: Optional[MiniPetContainer] = None
        self._online_peers: Dict[str, Dict[str, Any]] = {}
        
        self._is_dragging = False
        self._drag_position = QPoint()
        
        self._is_transitioning = False
        self._transition_target = None
        self._transition_step = 0
        
        self._last_time_text = ""
        self._current_label_style = None
        
        # 分类专注时长追踪
        self._last_english_seconds = 0
        self._last_coding_seconds = 0
        
        # 网络广播节流
        self._last_broadcast_state = ""
        
        # UI布局去重
        self._layout_dirty = True
        
        # 复习提纲对话框引用
        self._outline_dialog = None
        
        self._init_ui()
        self._init_mood()
        self._init_mini_pets()
        self._init_network()
        self._init_focus_monitor()
        self._init_save_timer()
    
    @property
    def pet_name(self) -> str:
        return self._pet_name
    
    @property
    def pet_id(self) -> str:
        return self._pet_id
    
    @property
    def local_ip(self) -> str:
        return self._local_ip
    
    @property
    def online_peers(self) -> Dict[str, Dict[str, Any]]:
        return self._online_peers.copy()
    
    @property
    def online_count(self) -> int:
        return len(self._online_peers)
    
    @property
    def is_transitioning(self) -> bool:
        return self._is_transitioning
    
    def _init_ui(self):
        """初始化UI"""
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.SubWindow
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        # 宠物图片标签
        self._pet_label = QLabel(self)
        self._pet_label.setAlignment(Qt.AlignCenter)
        
        # 专注时长标签
        self._time_label = QLabel(self)
        self._time_label.setAlignment(Qt.AlignCenter)
        self._time_label.setMinimumWidth(120)
        self._time_label.setStyleSheet("""
            QLabel {
                color: #333333;
                background-color: rgba(255, 255, 255, 200);
                border-radius: 10px;
                padding: 5px 12px;
                font-weight: bold;
            }
        """)
        self._time_label.setFont(QFont(self._cn_font, 10))
        self._time_label.hide()
        
        # 商店按钮
        self._shop_button = QPushButton("🏪", self)
        self._shop_button.setFixedSize(30, 30)
        self._shop_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 200);
                border: none;
                border-radius: 15px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 255);
            }
        """)
        self._shop_button.clicked.connect(self._show_shop_dialog)
        self._shop_button.setCursor(Qt.PointingHandCursor)
        
        # 复习提纲按钮（新增）
        self._outline_button = QPushButton("✏️", self)
        self._outline_button.setFixedSize(30, 30)
        self._outline_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 200);
                border: none;
                border-radius: 15px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 255);
            }
        """)
        self._outline_button.clicked.connect(self._open_upload_dialog)
        self._outline_button.setCursor(Qt.PointingHandCursor)
        
        screen = QApplication.primaryScreen().geometry()
        self.move(
            screen.width() - config.MAX_PET_WIDTH - config.DEFAULT_OFFSET_X,
            screen.height() - config.MAX_PET_HEIGHT - config.DEFAULT_OFFSET_Y
        )
        
        self.show()
    
    def _init_mood(self):
        """初始化表情"""
        character = "cat"
        if self._user_data:
            character = self._user_data.current_character or "cat"
        self._mood_manager.load_mood_images(character)
        self._update_pet_display()
    
    def _init_mini_pets(self):
        """初始化迷你宠物容器"""
        self._mini_pet_container = MiniPetContainer()
        self._mini_pet_container.set_main_pet_position(self.pos())
        self._mini_pet_container.set_main_pet_size((self.width(), self.height()))
    
    def _init_network(self):
        """初始化网络"""
        try:
            character = "cat"
            if self._user_data:
                character = self._user_data.current_character or "cat"
            self._network_manager = NetworkManager(self._pet_name, self._pet_id, character)
            
            self._network_manager.peer_discovered.connect(self._on_peer_discovered)
            self._network_manager.peer_lost.connect(self._on_peer_lost)
            self._network_manager.emotion_received.connect(self._on_emotion_received)
            self._network_manager.message_received.connect(self._on_message_received)
            self._network_manager.status_received.connect(self._on_status_received)
            self._network_manager.animation_received.connect(self._on_animation_received)
            # 修复：连接专注状态信号
            self._network_manager.focus_state_received.connect(self._on_focus_state_received)
            # 修复：TCP连接建立后再广播状态，替代之前的500ms盲等
            self._network_manager.connection_established.connect(self._on_connection_established)
            
            self._network_manager.start()
            print(f"[宠物] 网络启动成功 - ID: {self._pet_id}")
            
        except Exception as e:
            print(f"[宠物] 网络初始化失败: {e}")
            self._notification_manager.show_error("网络功能启动失败")
    
    def _init_focus_monitor(self):
        """初始化专注监控（后台线程）"""
        self._focus_worker = FocusWorker(
            self._focus_manager,
            interval_ms=config.MONITOR_INTERVAL,
            parent=self
        )
        self._focus_worker.focus_checked.connect(self._on_focus_checked)
        self._focus_worker.start()
    
    def _init_save_timer(self):
        """初始化定时保存"""
        self._save_timer = QTimer(self)
        self._save_timer.timeout.connect(self._periodic_save)
        self._save_timer.start(config.SAVE_INTERVAL * 1000)
    
    def _periodic_save(self):
        """定时保存"""
        if self._user_data:
            self._user_data.save()
    
    def _update_pet_display(self):
        """更新宠物显示"""
        self._layout_dirty = True
        
        if self._mood_manager.current_mood == MoodManager.HAPPY and self._user_data:
            skin_name = self._user_data.today_skin
            if skin_name:
                skin_pixmap = self._get_skin_pixmap(skin_name)
                if skin_pixmap:
                    self._pet_label.setPixmap(skin_pixmap)
                    self._pet_label.resize(skin_pixmap.size())
                    self.resize(skin_pixmap.size())
                    self._update_layout()
                    return
        
        pixmap = self._mood_manager.current_pixmap
        if pixmap:
            self._pet_label.setPixmap(pixmap)
            self._pet_label.resize(pixmap.size())
            self.resize(pixmap.size())
            
            if self._mini_pet_container:
                self._mini_pet_container.set_main_pet_position(self.pos())
                self._mini_pet_container.set_main_pet_size((self.width(), self.height()))
        
        self._update_layout()
    
    def _get_skin_pixmap(self, skin_name: str) -> Optional[QPixmap]:
        """获取皮肤图片，skin_name 如 'cat/lv0-1.png'"""
        skin_path = config.get_resource_path(config.SKINS_DIR, skin_name)
        if not skin_path or not os.path.exists(skin_path):
            return None
        
        pixmap = QPixmap(skin_path)
        if pixmap.isNull():
            return None
        
        if pixmap.width() > config.MAX_PET_WIDTH or pixmap.height() > config.MAX_PET_HEIGHT:
            pixmap = pixmap.scaled(
                config.MAX_PET_WIDTH,
                config.MAX_PET_HEIGHT,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        
        return pixmap
    
    def _update_layout(self):
        """更新布局（仅在标记脏时执行）"""
        if not self._layout_dirty:
            return
        self._layout_dirty = False
        
        pet_size = self._pet_label.size()
        pet_width = pet_size.width()
        pet_height = pet_size.height()
        
        # 商店按钮在左上角
        self._shop_button.move(0, 0)
        # 复习提纲按钮在商店按钮下方
        self._outline_button.move(0, 34)
        
        if self._time_label.isVisible():
            self._time_label.adjustSize()
            time_width = self._time_label.width()
            time_height = self._time_label.height()
            
            self._time_label.move(
                pet_width + 5,
                (pet_height - time_height) // 2
            )
            
            target_width = pet_width + time_width + 10
            target_height = max(pet_height, time_height)
            self.resize(target_width, target_height)
        else:
            self.resize(pet_size)
    
    # ==================== 过渡动画 ====================
    
    def set_mood(self, mood: str, with_animation: bool = True) -> bool:
        if mood not in self._mood_manager._mood_images:
            mood = MoodManager.STAND
        if mood not in self._mood_manager._mood_images:
            return False
        
        if mood == self._mood_manager.current_mood and not self._is_transitioning:
            return True
        
        if self._is_transitioning and mood == self._transition_target:
            return True
        
        if (with_animation and 
            self._mood_manager.has_transition() and 
            mood != self._mood_manager.current_mood and 
            not self._is_transitioning):
            
            self._is_transitioning = True
            self._transition_target = mood
            self._transition_step = 0
            
            self._broadcast_animation_start(mood)
            self._play_transition_step()
            return True
        
        self._apply_mood(mood)
        return True
    
    def _play_transition_step(self):
        if self._transition_step < self._mood_manager.stage_count:
            pixmap = self._mood_manager.get_stage_pixmap(self._transition_step)
            if pixmap:
                self._pet_label.setPixmap(pixmap)
                self._pet_label.resize(pixmap.size())
                self._layout_dirty = True
                self._update_layout()
                
                if self._mini_pet_container:
                    self._mini_pet_container.update_main_pet_stage(self._transition_step)
            
            self._transition_step += 1
            QTimer.singleShot(self.TRANSITION_INTERVAL, self._play_transition_step)
        else:
            self._is_transitioning = False
            target = self._transition_target
            self._transition_target = None
            self._apply_mood(target)
    
    def _apply_mood(self, mood: str):
        self._mood_manager.set_mood(mood)
        self._update_pet_display()
        self._broadcast_status()
    
    def _broadcast_animation_start(self, target_mood: str):
        if self._network_manager:
            self._network_manager.broadcast_animation(target_mood, self._mood_manager.stage_count)
    
    def _broadcast_status(self):
        if self._network_manager:
            self._network_manager.broadcast_status(self._mood_manager.current_mood)
    
    def _broadcast_current_state(self):
        """广播当前状态给所有连接的用户"""
        if self._network_manager:
            self._network_manager.broadcast_status(self._mood_manager.current_mood)
            state = self._focus_manager.current_state
            self._network_manager.broadcast_focus_state(
                state,
                self._focus_manager.focus_seconds,
                self._focus_manager.play_seconds
            )
    
    # ==================== 专注监控 ====================
    
    def _on_focus_checked(self, state: str, info: dict):
        """接收后台线程的检测结果（在UI线程执行）"""
        if info.get("timer_only"):
            self._update_time_display()
            return
        
        if state == FocusManager.STATE_STUDY:
            self._handle_study_state(info)
        elif state == FocusManager.STATE_ENTERTAINMENT:
            self._handle_entertainment_state(info)
        else:
            self._handle_neutral_state()
    
    def _handle_study_state(self, info: dict):
        if self._mood_manager.current_mood != MoodManager.HAPPY:
            self.set_mood(MoodManager.HAPPY)
        
        self._update_time_display()

        if self._network_manager and self._last_broadcast_state != "study":
            self._last_broadcast_state = "study"
            self._network_manager.broadcast_focus_state(
                "study", 
                self._focus_manager.focus_seconds, 
                0
            )

    def _handle_entertainment_state(self, info: dict):
        if self._mood_manager.current_mood != MoodManager.SAD:
            self.set_mood(MoodManager.SAD)
        
        self._update_play_time_display()

        if self._network_manager and self._last_broadcast_state != "entertainment":
            self._last_broadcast_state = "entertainment"
            self._network_manager.broadcast_focus_state(
                "entertainment", 
                0, 
                self._focus_manager.play_seconds
            )

    def _handle_neutral_state(self):
        if self._mood_manager.current_mood != MoodManager.STAND:
            self.set_mood(MoodManager.STAND)
        
        # 重置分类专注追踪指针
        self._last_english_seconds = 0
        self._last_coding_seconds = 0
        
        if self._time_label.isVisible():
            self._time_label.hide()
            self._layout_dirty = True
            self._update_layout()

        if self._network_manager and self._last_broadcast_state != "neutral":
            self._last_broadcast_state = "neutral"
            self._network_manager.broadcast_focus_state("neutral", 0, 0)

    def _update_time_display(self):
        time_text = self._focus_manager.get_focus_time_text()
        
        if time_text != self._last_time_text:
            self._last_time_text = time_text
            self._time_label.setText(time_text)
        
        if self._current_label_style != "focus":
            self._current_label_style = "focus"
            self._time_label.setStyleSheet("""
                QLabel {
                    color: #333333;
                    background-color: rgba(255, 255, 255, 200);
                    border-radius: 10px;
                    padding: 5px 12px;
                    font-weight: bold;
                }
            """)
        
        if not self._time_label.isVisible():
            self._time_label.show()
            self._layout_dirty = True
            self._update_layout()
        
        self._update_coins()
    
    def _update_play_time_display(self):
        time_text = self._focus_manager.get_play_time_text()
        
        if time_text != self._last_time_text:
            self._last_time_text = time_text
            self._time_label.setText(time_text)
        
        if self._current_label_style != "play":
            self._current_label_style = "play"
            self._time_label.setStyleSheet("""
                QLabel {
                    color: #FF6B6B;
                    background-color: rgba(255, 255, 255, 200);
                    border-radius: 10px;
                    padding: 5px 12px;
                    font-weight: bold;
                }
            """)
        
        if not self._time_label.isVisible():
            self._time_label.show()
            self._layout_dirty = True
            self._update_layout()
    
    def _update_coins(self):
        if self._user_data and self._focus_manager.is_studying:
            current_focus = self._focus_manager.focus_seconds
            daily_so_far = self._user_data.daily_focus_seconds
            
            if current_focus > daily_so_far:
                new_seconds = current_focus - daily_so_far
                self._user_data.add_focus_time(new_seconds)
            
            # 追踪分类专注时长
            study_type = self._focus_manager.current_study_type
            if study_type == FocusManager.STUDY_TYPE_ENGLISH:
                if current_focus > self._last_english_seconds:
                    delta = current_focus - self._last_english_seconds
                    self._user_data.add_english_focus_time(delta)
                    self._last_english_seconds = current_focus
                    self._last_coding_seconds = current_focus
            elif study_type == FocusManager.STUDY_TYPE_CODING:
                if current_focus > self._last_coding_seconds:
                    delta = current_focus - self._last_coding_seconds
                    self._user_data.add_coding_focus_time(delta)
                    self._last_coding_seconds = current_focus
                    self._last_english_seconds = current_focus
            else:
                # general 类型不累计分类时长，但同步指针
                self._last_english_seconds = current_focus
                self._last_coding_seconds = current_focus
    
    def _show_shop_dialog(self):
        def on_skin_selected(skin_path):
            if self._mood_manager.current_mood == MoodManager.HAPPY:
                self._update_pet_display()
        
        def on_character_changed(character):
            if character != self._mood_manager.current_character:
                self._mood_manager.load_mood_images(character)
                self._update_pet_display()
                if self._mini_pet_container:
                    self._mini_pet_container.set_main_pet_position(self.pos())
                    self._mini_pet_container.set_main_pet_size((self.width(), self.height()))
                if self._network_manager:
                    self._network_manager.set_character(character)
        
        dialog = ShopDialog(self._user_data, on_skin_selected, on_character_changed, self)
        dialog.show_near_pet(self.mapToGlobal(QPoint(0, 0)), self.width())
        dialog.exec_()
    
    def _open_upload_dialog(self):
        """打开复习提纲对话框"""
        from ui.study_outline import FileUploadDialog
        
        # 进入专注状态
        def on_focus_start():
            if self._mood_manager.current_mood != MoodManager.HAPPY:
                self.set_mood(MoodManager.HAPPY)
        
        self._outline_dialog = FileUploadDialog(
            self, 
            font_family=self._cn_font,
            on_focus_start=on_focus_start
        )
        self._outline_dialog.show_near_pet(self.mapToGlobal(QPoint(0, 0)), self.width())
        self._outline_dialog.exec_()
    
    def get_available_moods(self):
        return self._mood_manager.available_moods
    
    # ==================== 网络事件处理 ====================
    
    def _on_peer_discovered(self, peer_info: Dict[str, Any]):
        peer_id = peer_info["id"]
        peer_name = peer_info.get("name", "未知用户")
        peer_character = peer_info.get("character", "cat")
        
        print(f"[宠物] 发现新用户: {peer_name} ({peer_id}), 角色: {peer_character}")
        
        self._online_peers[peer_id] = peer_info
        
        if self._mini_pet_container:
            self._mini_pet_container.add_peer(peer_id, peer_name, peer_character)
        
        self._notification_manager.show_info(f"👋 {peer_name} 加入了网络")
    
    def _on_connection_established(self, peer_id: str):
        """TCP连接建立后广播当前状态给对方"""
        print(f"[宠物] TCP连接已建立: {peer_id}，广播当前状态")
        self._broadcast_current_state()
    
    def _on_peer_lost(self, peer_info: Dict[str, Any]):
        peer_id = peer_info["id"]
        peer_name = peer_info.get("name", "未知用户")
        
        print(f"[宠物] 用户离开: {peer_name} ({peer_id})")
        
        self._online_peers.pop(peer_id, None)
        
        if self._mini_pet_container:
            self._mini_pet_container.remove_peer(peer_id)
        
        self._notification_manager.show_info(f"👋 {peer_name} 离开了网络")
    
    def _on_emotion_received(self, data: Dict[str, Any]):
        sender_id = data["sender_id"]
        emotion = data.get("emotion", "happy")
        
        if self._mini_pet_container:
            self._mini_pet_container.show_peer_emotion(sender_id, emotion)
    
    def _on_message_received(self, data: Dict[str, Any]):
        sender_id = data["sender_id"]
        message = data.get("message", "")
        
        if self._mini_pet_container:
            self._mini_pet_container.show_peer_message(sender_id, message)
    
    def _on_status_received(self, data: Dict[str, Any]):
        sender_id = data["sender_id"]
        mood = data.get("mood", "stand")
        character = data.get("character", "cat")
        
        if self._mini_pet_container:
            self._mini_pet_container.update_peer_mood(sender_id, mood, character)
    
    def _on_animation_received(self, data: Dict[str, Any]):
        sender_id = data["sender_id"]
        target_mood = data.get("target_mood", "stand")
        stage_count = data.get("stage_count", 0)
        character = data.get("character", "cat")
        
        if self._mini_pet_container:
            self._mini_pet_container.play_peer_animation(sender_id, target_mood, stage_count, character)
    
    def _on_focus_state_received(self, data: Dict[str, Any]):
        sender_id = data["sender_id"]
        state = data.get("state", "neutral")
        focus_seconds = data.get("focus_seconds", 0)
        play_seconds = data.get("play_seconds", 0)
        
        if self._mini_pet_container:
            self._mini_pet_container.update_peer_focus_state(
                sender_id, state, focus_seconds, play_seconds
            )
    
    # ==================== 网络操作 ====================
    
    def send_emotion_to_all(self, emotion: str):
        if self._network_manager:
            self._network_manager.send_emotion(emotion)
            if self._user_data:
                self._user_data.increment_emotions()
            self._notification_manager.show_info(f"已发送 {config.EMOTION_EMOJI.get(emotion, emotion)} 表情")
    
    def send_emotion_to_user(self, emotion: str, peer_id: str, peer_name: str = None):
        if self._network_manager:
            self._network_manager.send_emotion(emotion, peer_id)
            if self._user_data:
                self._user_data.increment_emotions()
    
    def send_message_to_all(self, message: str):
        if self._network_manager:
            self._network_manager.send_message(message)
            if self._user_data:
                self._user_data.increment_messages()
            self._notification_manager.show_info("消息已发送")
    
    def send_message_to_user(self, message: str, peer_id: str, peer_name: str = None):
        if self._network_manager:
            self._network_manager.send_message(message, peer_id)
            if self._user_data:
                self._user_data.increment_messages()
    
    def get_network_info(self) -> Dict[str, Any]:
        info = {
            "network_available": self._network_manager is not None,
            "local_ip": self._local_ip,
            "pet_id": self._pet_id,
            "pet_name": self._pet_name,
            "online_count": self.online_count,
            "peers": list(self._online_peers.values()),
            "mini_pet_count": self._mini_pet_container.get_peer_count() if self._mini_pet_container else 0
        }
        
        if self._network_manager:
            info["tcp_connections"] = self._network_manager.connection_count
        
        return info
    
    # ==================== 鼠标事件 ====================
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())
            event.accept()
    
    def mouseMoveEvent(self, event):
        if self._is_dragging and event.buttons() & Qt.LeftButton:
            new_pos = event.globalPos() - self._drag_position
            self.move(new_pos)
            
            if self._mini_pet_container:
                self._mini_pet_container.set_main_pet_position(new_pos)
            
            event.accept()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = False
            event.accept()
    
    def enterEvent(self, event):
        self.setCursor(QCursor(Qt.OpenHandCursor))
    
    def leaveEvent(self, event):
        self.setCursor(QCursor(Qt.ArrowCursor))
    
    def _show_context_menu(self, pos):
        menu = ContextMenu(self)
        menu.exec_(pos)
    
    # ==================== 清理 ====================
    
    def cleanup(self):
        print("[宠物] 开始清理资源...")
        
        # 停止后台线程
        if hasattr(self, '_focus_worker'):
            self._focus_worker.stop()
        
        if self._user_data:
            self._user_data.save(force=True)
        
        if self._mini_pet_container:
            self._mini_pet_container.clear_all()
            self._mini_pet_container.close()
        
        if self._network_manager:
            self._network_manager.stop()
        
        print("[宠物] 资源清理完成")