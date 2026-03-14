# -*- coding: utf-8 -*-
"""
表情管理器 - 负责加载和管理宠物表情（含过渡动画）
"""
import os
from typing import Dict, Optional, List
from PyQt5.QtGui import QPixmap, QPainter, QColor
from PyQt5.QtCore import Qt

import config


class MoodManager:
    """表情管理器"""
    
    # 表情常量
    STAND = "stand"
    HAPPY = "happy"
    SAD = "sad"
    LOVE = "love"
    ANGRY = "angry"
    SURPRISE = "surprise"
    
    DEFAULT_MOODS = [STAND, HAPPY, SAD]
    
    def __init__(self):
        self._mood_images: Dict[str, QPixmap] = {}
        self._stage_images: List[QPixmap] = []  # 过渡帧图片列表
        self._scaled_cache: Dict[str, Dict[int, QPixmap]] = {}
        self._stage_scaled_cache: Dict[int, List[QPixmap]] = {}  # 过渡帧缩放缓存
        self._current_mood: str = self.STAND
        self._current_character: str = "cat"
    
    @property
    def current_mood(self) -> str:
        return self._current_mood
    
    @property
    def available_moods(self) -> List[str]:
        return list(self._mood_images.keys())
    
    @property
    def current_pixmap(self) -> Optional[QPixmap]:
        return self._mood_images.get(self._current_mood)
    
    @property
    def stage_count(self) -> int:
        """过渡帧数量"""
        return len(self._stage_images)
    
    def has_transition(self) -> bool:
        """是否有过渡动画"""
        return len(self._stage_images) > 0
    
    @property
    def current_character(self) -> str:
        return self._current_character
    
    def load_mood_images(self, character: str = "cat") -> bool:
        """加载表情图片"""
        self._current_character = character
        
        # 清除旧缓存
        self._mood_images.clear()
        self._stage_images.clear()
        self._scaled_cache.clear()
        self._stage_scaled_cache.clear()
        
        base_path = config.get_resource_path(
            config.ANIMATIONS_DIR,
            config.ANIMATION_IDLE,
            character
        )
        
        # 加载所有表情图片
        for mood in self.DEFAULT_MOODS:
            image_path = os.path.join(base_path, f"{mood}.png")
            self._load_single_mood(mood, image_path)
        
        # 加载过渡帧
        self._load_stage_images(base_path)
        
        # 如果没有加载到任何图片，创建占位图
        if not self._mood_images:
            self._create_placeholder()
            return False
        
        # 设置默认表情
        self.set_mood(self.STAND)
        return True
    
    def _load_single_mood(self, mood: str, image_path: str) -> bool:
        """加载单个表情图片"""
        if not os.path.exists(image_path):
            return False
        
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            return False
        
        # 缩放到合适大小
        if pixmap.width() > config.MAX_PET_WIDTH or pixmap.height() > config.MAX_PET_HEIGHT:
            pixmap = pixmap.scaled(
                config.MAX_PET_WIDTH,
                config.MAX_PET_HEIGHT,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        
        self._mood_images[mood] = pixmap
        print(f"[表情] 加载成功: {mood}")
        return True
    
    def _load_stage_images(self, base_path: str):
        """加载过渡帧图片"""
        for i in range(1, 10):  # 最多支持9帧过渡
            stage_path = os.path.join(base_path, f"stage{i}.png")
            if os.path.exists(stage_path):
                pixmap = QPixmap(stage_path)
                if not pixmap.isNull():
                    if pixmap.width() > config.MAX_PET_WIDTH or pixmap.height() > config.MAX_PET_HEIGHT:
                        pixmap = pixmap.scaled(
                            config.MAX_PET_WIDTH,
                            config.MAX_PET_HEIGHT,
                            Qt.KeepAspectRatio,
                            Qt.SmoothTransformation
                        )
                    self._stage_images.append(pixmap)
        
        if self._stage_images:
            print(f"[表情] 加载过渡帧: {len(self._stage_images)} 帧")
    
    def _create_placeholder(self) -> None:
        """创建占位图"""
        pixmap = QPixmap(150, 150)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.setBrush(QColor(100, 200, 255, 200))
        painter.setPen(QColor(50, 150, 200))
        painter.drawEllipse(10, 10, 130, 130)
        
        painter.setBrush(QColor(0, 0, 0))
        painter.drawEllipse(45, 50, 20, 20)
        painter.drawEllipse(85, 50, 20, 20)
        
        painter.drawArc(40, 60, 70, 50, -30 * 16, -120 * 16)
        painter.end()
        
        self._mood_images[self.STAND] = pixmap
        print("[表情] 使用占位图")
    
    def set_mood(self, mood: str) -> bool:
        """设置当前表情"""
        if mood not in self._mood_images:
            if self.STAND in self._mood_images:
                mood = self.STAND
            else:
                return False
        
        self._current_mood = mood
        return True
    
    def has_mood(self, mood: str) -> bool:
        return mood in self._mood_images
    
    def get_scaled_pixmap(self, mood: str, scale: int) -> Optional[QPixmap]:
        """获取缩放后的表情图片"""
        if mood not in self._mood_images:
            mood = self.STAND
        
        if mood not in self._mood_images:
            return None
        
        if mood not in self._scaled_cache:
            self._scaled_cache[mood] = {}
        
        if scale in self._scaled_cache[mood]:
            return self._scaled_cache[mood][scale]
        
        original = self._mood_images[mood]
        new_width = original.width() // scale
        new_height = original.height() // scale
        
        scaled = original.scaled(
            new_width, new_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        self._scaled_cache[mood][scale] = scaled
        return scaled
    
    def get_stage_pixmap(self, index: int) -> Optional[QPixmap]:
        """获取过渡帧图片"""
        if 0 <= index < len(self._stage_images):
            return self._stage_images[index]
        return None
    
    def get_scaled_stage_pixmap(self, index: int, scale: int) -> Optional[QPixmap]:
        """获取缩放后的过渡帧图片"""
        if not (0 <= index < len(self._stage_images)):
            return None
        
        # 检查缓存
        if scale not in self._stage_scaled_cache:
            self._stage_scaled_cache[scale] = {}
        
        if index in self._stage_scaled_cache[scale]:
            return self._stage_scaled_cache[scale][index]
        
        # 缩放
        original = self._stage_images[index]
        new_width = original.width() // scale
        new_height = original.height() // scale
        
        scaled = original.scaled(
            new_width, new_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        self._stage_scaled_cache[scale][index] = scaled
        return scaled