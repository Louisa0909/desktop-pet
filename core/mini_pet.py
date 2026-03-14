# -*- coding: utf-8 -*-
"""
迷你宠物组件 - 显示其他用户的宠物（含悬浮提示）
"""
import random
from typing import Optional, TYPE_CHECKING
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect, QFrame
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QPoint, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QColor, QPainter

import config

if TYPE_CHECKING:
    from .mood_manager import MoodManager


class HoverInfoTip(QWidget):
    """
    悬浮提示条 - 显示用户名和专注状态
    两行：第一行用户名，第二行专注状态
    """
    
    def __init__(self, parent: QWidget = None):
        super().__init__(None)  # 独立窗口
        
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowTransparentForInput  # 鼠标事件穿透
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self._hide_timer = QTimer()
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        # 主容器
        self._container = QWidget(self)
        self._container.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 253, 247, 245);
                border-radius: 12px;
                border: 2px solid #FFE4C4;
            }
        """)
        
        layout = QVBoxLayout(self._container)
        layout.setSpacing(4)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # 获取字体
        font_family = self._get_font_family()
        
        # 第一行：用户名
        self._name_label = QLabel()
        self._name_label.setFont(QFont(font_family, 11, QFont.Bold))
        self._name_label.setStyleSheet("color: #FF9966; border: none; background: transparent;")
        self._name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._name_label)
        
        # 分隔线
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #FFE4C4; border: none;")
        layout.addWidget(separator)
        
        # 第二行：状态
        self._status_label = QLabel()
        self._status_label.setFont(QFont(font_family, 10))
        self._status_label.setStyleSheet("color: #666666; border: none; background: transparent;")
        self._status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._status_label)
        
        self._container.adjustSize()
        self.adjustSize()
        
        self.hide()
    
    def _get_font_family(self) -> str:
        """获取中文字体"""
        from ui.shop_dialog import find_chinese_font
        return find_chinese_font() or "Microsoft YaHei"
    
    def show_info(self, name: str, status: str, global_pos: QPoint):
        """
        显示提示信息
        
        Args:
            name: 用户名
            status: 状态文本（如"专注 10m30s"或"玩耍 5m20s"）
            global_pos: 显示位置（全局坐标）
        """
        self._hide_timer.stop()
        
        # 更新内容
        self._name_label.setText(f"👤 {name}")
        self._status_label.setText(status)
        
        # 根据状态设置颜色
        if status.startswith("专注"):
            self._status_label.setStyleSheet("color: #4CAF50; border: none; background: transparent;")
        elif status.startswith("玩耍"):
            self._status_label.setStyleSheet("color: #FF6B6B; border: none; background: transparent;")
        else:
            self._status_label.setStyleSheet("color: #666666; border: none; background: transparent;")
        
        # 调整大小
        self._name_label.adjustSize()
        self._status_label.adjustSize()
        self._container.adjustSize()
        self.adjustSize()
        
        # 计算显示位置（在迷你宠物上方）
        x = global_pos.x() + 10
        y = global_pos.y() - self.height() - 8
        
        # 确保不超出屏幕
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            if x + self.width() > screen_geo.right():
                x = screen_geo.right() - self.width() - 10
            if y < screen_geo.top():
                y = global_pos.y() + 50  # 显示在下方
        
        self.move(x, y)
        self.show()
    
    def hide_delayed(self, delay: int = 300):
        """延迟隐藏"""
        self._hide_timer.start(delay)
    
    def hide_immediate(self):
        """立即隐藏"""
        self._hide_timer.stop()
        self.hide()


class EmotionLabel(QLabel):
    """表情emoji显示标签"""
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._hide_timer = QTimer()
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet("background: transparent; border: none; color: black;")
        font = QFont()
        font.setPointSize(16)
        self.setFont(font)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.hide()
    
    def show_emotion(self, emoji: str, duration: int):
        self._hide_timer.stop()
        self.setText(emoji)
        self.adjustSize()
        self.raise_()
        self.show()
        self._hide_timer.start(duration)


class MessageBubbleWidget(QWidget):
    """消息气泡 - 使用独立窗口"""
    
    closed = pyqtSignal()
    
    def __init__(self, parent: QWidget = None):
        super().__init__(None)
        self._char_timer = QTimer()
        self._char_timer.timeout.connect(self._show_next_char)
        self._full_text = ""
        self._current_index = 0
        self._target_pos = QPoint(0, 0)
        self._opacity = 1.0
        self._fade_timer = QTimer()
        self._fade_timer.timeout.connect(self._fade_step)
        self._shake_count = 0
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        
        self._label = QLabel(self)
        self._label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 245);
                color: #333333;
                padding: 8px 12px;
                border-radius: 12px;
                border: 2px solid #AAAAAA;
            }
        """)
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self._label.setFont(font)
        self._label.setWordWrap(True)
        self._label.setMaximumWidth(150)
        self._label.setMinimumWidth(40)
        self._label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._label.hide()
        
        self.hide()
    
    def show_message(self, text: str, duration: int, global_pos: QPoint = None):
        self._char_timer.stop()
        self._fade_timer.stop()
        self._opacity = 1.0
        self.setWindowOpacity(1.0)
        
        if len(text) > config.MESSAGE_MAX_LENGTH:
            text = text[:config.MESSAGE_MAX_LENGTH - 3] + "..."
        
        self._full_text = text
        self._current_index = 0
        self._shake_count = 0
        
        self._label.setText(text)
        self._label.adjustSize()
        self._label.resize(self._label.sizeHint())
        
        self.resize(self._label.width() + 16, self._label.height() + 8)
        
        if global_pos:
            self.move(global_pos)
            self._target_pos = global_pos
        
        self._label.setText("")
        self._label.move(8, 4)
        self._label.show()
        self.show()
        
        self._char_timer.start(50)
        QTimer.singleShot(duration, self._start_fade_out)
    
    def _show_next_char(self):
        if self._current_index >= len(self._full_text):
            self._char_timer.stop()
            return
        
        self._current_index += 1
        current_text = self._full_text[:self._current_index]
        self._label.setText(current_text)
        self._apply_shake()
    
    def _apply_shake(self):
        if self._shake_count < 15:
            offset_x = random.randint(-2, 2)
            offset_y = random.randint(-1, 1)
            self.move(
                self._target_pos.x() + offset_x,
                self._target_pos.y() + offset_y
            )
            self._shake_count += 1
        else:
            self.move(self._target_pos)
    
    def _start_fade_out(self):
        self._fade_timer.start(40)
    
    def _fade_step(self):
        self._opacity -= 0.05
        if self._opacity <= 0:
            self._fade_timer.stop()
            self.hide()
            self._label.setText("")
            self._opacity = 1.0
            self.closed.emit()
        else:
            self.setWindowOpacity(self._opacity)


class MiniPetWidget(QWidget):
    """单个迷你宠物组件"""
    
    MOOD_STAND = "stand"
    TRANSITION_INTERVAL = 200
    
    def __init__(self, peer_id: str, peer_name: str, character: str = "cat", parent: QWidget = None):
        super().__init__(parent)
        self._peer_id = peer_id
        self._peer_name = peer_name
        self._current_mood = self.MOOD_STAND
        
        # 每个迷你宠物使用独立的 MoodManager，加载对方的角色图片
        from .mood_manager import MoodManager
        self._mood_manager = MoodManager()
        self._mood_manager.load_mood_images(character)
        
        # 专注状态数据
        self._focus_state = "neutral"  # "study", "entertainment", "neutral"
        self._focus_seconds = 0
        self._play_seconds = 0
        
        # 动画状态
        self._is_animating = False
        self._animation_target = None
        self._animation_step = 0
        self._animation_total_frames = 0
        
        # 悬停计时器（用于延迟显示提示）
        self._hover_timer = QTimer()
        self._hover_timer.setSingleShot(True)
        self._hover_timer.timeout.connect(self._show_hover_tip)
        self._is_hovering = False
        
        self._setup_ui()
        self._create_overlays()
    
    @property
    def peer_id(self) -> str:
        return self._peer_id
    
    @property
    def peer_name(self) -> str:
        return self._peer_name
    
    def _setup_ui(self):
        self._pet_label = QLabel(self)
        self._pet_label.setAlignment(Qt.AlignCenter)
        
        self._name_label = QLabel(self._peer_name, self)
        self._name_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 200);
                color: white;
                padding: 3px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        self._name_label.adjustSize()
        self._name_label.hide()
        
        self._update_display()
    
    def _create_overlays(self):
        self._emotion_label = EmotionLabel(self)
        self._message_bubble = MessageBubbleWidget()
        self._hover_tip = HoverInfoTip()  # 悬浮提示
    
    def _update_display(self):
        scale = config.MINI_PET_SCALE
        pixmap = self._mood_manager.get_scaled_pixmap(self._current_mood, scale)
        
        if pixmap:
            self._pet_label.setPixmap(pixmap)
            self._pet_label.resize(pixmap.size())
            self.resize(pixmap.size())
        else:
            default_size = config.MAX_PET_WIDTH // scale
            self.resize(default_size, default_size)
        
        self._name_label.move(
            (self.width() - self._name_label.width()) // 2,
            self.height() + 3
        )
    
    def set_mood(self, mood: str):
        """设置表情状态"""
        if mood != self._current_mood:
            self._current_mood = mood
            self._update_display()
    
    def set_character(self, character: str):
        """切换角色类型（当对方角色变化时调用）"""
        if character != self._mood_manager.current_character:
            self._mood_manager.load_mood_images(character)
            self._update_display()
    
    def set_focus_state(self, state: str, focus_seconds: int = 0, play_seconds: int = 0):
        """
        设置专注状态
        
        Args:
            state: 状态 ("study", "entertainment", "neutral")
            focus_seconds: 专注秒数
            play_seconds: 玩耍秒数
        """
        self._focus_state = state
        self._focus_seconds = focus_seconds
        self._play_seconds = play_seconds
        
        # 如果正在悬停，更新提示
        if self._is_hovering:
            self._show_hover_tip()
    
    def get_status_text(self) -> str:
        """获取状态文本"""
        if self._focus_state == "study":
            minutes = self._focus_seconds // 60
            seconds = self._focus_seconds % 60
            return f"专注 {minutes}m{seconds}s"
        elif self._focus_state == "entertainment":
            minutes = self._play_seconds // 60
            seconds = self._play_seconds % 60
            return f"玩耍 {minutes}m{seconds}s"
        else:
            return "普通状态"
    
    def show_emotion(self, emotion: str):
        emoji = config.EMOTION_EMOJI.get(emotion, "💬")
        self._emotion_label.move(-2, -2)
        self._emotion_label.show_emotion(emoji, config.EMOTION_DISPLAY_DURATION)
    
    def show_message(self, message: str):
        bubble_x = self.width() + 10
        bubble_y = max(0, (self.height() - 30) // 2)
        global_pos = self.mapToGlobal(QPoint(bubble_x, bubble_y))
        
        self._message_bubble.show_message(
            message,
            config.MESSAGE_DISPLAY_DURATION,
            global_pos
        )
    
    def play_animation(self, target_mood: str, stage_count: int):
        if self._is_animating:
            return
        
        self._is_animating = True
        self._animation_target = target_mood
        self._animation_step = 0
        self._animation_total_frames = min(stage_count, self._mood_manager.stage_count)
        
        if self._animation_total_frames > 0:
            self._play_animation_step()
        else:
            self._is_animating = False
            self.set_mood(target_mood)
    
    def _play_animation_step(self):
        if self._animation_step < self._animation_total_frames:
            scale = config.MINI_PET_SCALE
            pixmap = self._mood_manager.get_scaled_stage_pixmap(self._animation_step, scale)
            
            if pixmap:
                self._pet_label.setPixmap(pixmap)
                self._pet_label.resize(pixmap.size())
                self.resize(pixmap.size())
            
            self._animation_step += 1
            QTimer.singleShot(self.TRANSITION_INTERVAL, self._play_animation_step)
        else:
            self._is_animating = False
            self.set_mood(self._animation_target)
    
    def _show_hover_tip(self):
        """显示悬浮提示"""
        if not self._is_hovering:
            return
        
        status_text = self.get_status_text()
        global_pos = self.mapToGlobal(QPoint(0, 0))
        self._hover_tip.show_info(self._peer_name, status_text, global_pos)
    
    def _hide_hover_tip(self):
        """隐藏悬浮提示"""
        self._is_hovering = False
        self._hover_tip.hide_delayed(200)
    
    def cleanup(self):
        if hasattr(self, '_message_bubble') and self._message_bubble:
            self._message_bubble.close()
        if hasattr(self, '_hover_tip') and self._hover_tip:
            self._hover_tip.close()
    
    def enterEvent(self, event):
        self._name_label.show()
        self._is_hovering = True
        self._hover_timer.start(500)  # 500ms后显示提示
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._name_label.hide()
        self._hover_timer.stop()
        self._hide_hover_tip()
        super().leaveEvent(event)


class MiniPetContainer(QWidget):
    """迷你宠物容器"""
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._mini_pets: dict = {}
        self._main_pet_pos = QPoint(0, 0)
        self._main_pet_size = (config.MAX_PET_WIDTH, config.MAX_PET_HEIGHT)
        
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        
        self._update_size()
    
    def set_main_pet_position(self, pos: QPoint):
        self._main_pet_pos = pos
        self._update_position()
    
    def set_main_pet_size(self, size: tuple):
        self._main_pet_size = size
        self._update_position()
    
    def _update_position(self):
        self.move(
            self._main_pet_pos.x() + self._main_pet_size[0] + 5,
            self._main_pet_pos.y()
        )
    
    def _update_size(self):
        scale = config.MINI_PET_SCALE
        pet_width = config.MAX_PET_WIDTH // scale
        pet_height = config.MAX_PET_HEIGHT // scale
        spacing = config.MINI_PET_SPACING
        
        count = min(len(self._mini_pets), config.MAX_MINI_PETS_DISPLAY)
        
        if count == 0:
            self.resize(0, 0)
            self.hide()
        else:
            self.resize(
                pet_width + 160,
                count * pet_height + (count - 1) * spacing + 20
            )
            self.show()
    
    def add_peer(self, peer_id: str, peer_name: str, character: str = "cat"):
        if peer_id in self._mini_pets:
            return
        
        if len(self._mini_pets) >= config.MAX_MINI_PETS_DISPLAY:
            return
        
        mini_pet = MiniPetWidget(peer_id, peer_name, character, self)
        self._mini_pets[peer_id] = mini_pet
        
        self._relayout()
        mini_pet.show()
        self._update_size()
    
    def remove_peer(self, peer_id: str):
        if peer_id not in self._mini_pets:
            return
        
        mini_pet = self._mini_pets.pop(peer_id)
        mini_pet.cleanup()
        mini_pet.deleteLater()
        
        self._relayout()
        self._update_size()
    
    def _relayout(self):
        scale = config.MINI_PET_SCALE
        pet_height = config.MAX_PET_HEIGHT // scale
        spacing = config.MINI_PET_SPACING
        
        y = 0
        for mini_pet in self._mini_pets.values():
            mini_pet.move(0, y)
            y += pet_height + spacing
    
    def update_peer_mood(self, peer_id: str, mood: str, character: str = None):
        if peer_id in self._mini_pets:
            if character:
                self._mini_pets[peer_id].set_character(character)
            self._mini_pets[peer_id].set_mood(mood)
    
    def update_peer_focus_state(self, peer_id: str, state: str, 
                                 focus_seconds: int = 0, play_seconds: int = 0):
        """更新对等节点的专注状态"""
        if peer_id in self._mini_pets:
            self._mini_pets[peer_id].set_focus_state(state, focus_seconds, play_seconds)
    
    def show_peer_emotion(self, peer_id: str, emotion: str):
        if peer_id in self._mini_pets:
            self._mini_pets[peer_id].show_emotion(emotion)
    
    def show_peer_message(self, peer_id: str, message: str):
        if peer_id in self._mini_pets:
            self._mini_pets[peer_id].show_message(message)
    
    def play_peer_animation(self, peer_id: str, target_mood: str, stage_count: int, character: str = None):
        if peer_id in self._mini_pets:
            if character:
                self._mini_pets[peer_id].set_character(character)
            self._mini_pets[peer_id].play_animation(target_mood, stage_count)
    
    def update_main_pet_stage(self, stage_index: int):
        """更新主宠物的动画帧显示（占位方法）"""
        pass
    
    def get_peer_count(self) -> int:
        return len(self._mini_pets)
    
    def clear_all(self):
        for mini_pet in list(self._mini_pets.values()):
            mini_pet.cleanup()
            mini_pet.deleteLater()
        self._mini_pets.clear()
        self._update_size()