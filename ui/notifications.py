# -*- coding: utf-8 -*-
"""
通知气泡组件
"""
from typing import Optional
from PyQt5.QtWidgets import QLabel, QWidget
from PyQt5.QtCore import QTimer, QPropertyAnimation
from PyQt5.QtGui import QFont

import config


class NotificationBubble(QLabel):
    """通知气泡"""
    
    def __init__(self, text: str, parent: QWidget, style: dict = None):
        super().__init__(text, parent)
        
        # 默认样式
        default_style = {
            "background": "rgba(0, 0, 0, 180)",
            "color": "white",
            "padding": "5px 10px",
            "border_radius": "5px",
            "font_size": "11px"
        }
        
        style = style or default_style
        
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {style.get('background', default_style['background'])};
                color: {style.get('color', default_style['color'])};
                padding: {style.get('padding', default_style['padding'])};
                border-radius: {style.get('border_radius', default_style['border_radius'])};
                font-size: {style.get('font_size', default_style['font_size'])};
            }}
        """)
        
        self.adjustSize()
    
    def show_and_fade(self, duration: int = 3000):
        """显示并淡出"""
        self.show()
        
        # 淡出动画
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(duration)
        self._fade_animation.setStartValue(1.0)
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.finished.connect(self.deleteLater)
        self._fade_animation.start()


class NotificationManager:
    """通知管理器 - 简化版，主要用于系统通知"""
    
    def __init__(self, parent: QWidget):
        self._parent = parent
    
    def _show_bubble(self, text: str, style: dict = None, duration: int = 3000):
        """显示气泡"""
        bubble = NotificationBubble(text, self._parent, style)
        
        # 定位到宠物上方
        bubble.move(
            (self._parent.width() - bubble.width()) // 2,
            -bubble.height() - 5
        )
        
        bubble.show_and_fade(duration)
    
    def show_info(self, text: str, duration: int = 3000):
        """显示信息通知"""
        style = {
            "background": "rgba(0, 0, 0, 180)",
            "color": "white",
            "padding": "5px 10px",
            "border_radius": "5px",
            "font_size": "11px"
        }
        self._show_bubble(text, style, duration)
    
    def show_error(self, text: str, duration: int = 3000):
        """显示错误通知"""
        style = {
            "background": "rgba(200, 50, 50, 180)",
            "color": "white",
            "padding": "5px 10px",
            "border_radius": "5px",
            "font_size": "11px"
        }
        self._show_bubble(f"❌ {text}", style, duration)
    
    def show_success(self, text: str, duration: int = 3000):
        """显示成功通知"""
        style = {
            "background": "rgba(50, 150, 50, 180)",
            "color": "white",
            "padding": "5px 10px",
            "border_radius": "5px",
            "font_size": "11px"
        }
        self._show_bubble(f"✓ {text}", style, duration)