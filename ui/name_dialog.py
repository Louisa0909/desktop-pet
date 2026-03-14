#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
宠物命名对话框 - 与专注商店统一风格
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, 
    QLabel, QLineEdit, QPushButton
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


def find_chinese_font() -> str:
    """检测系统中可用的中文字体"""
    from PyQt5.QtGui import QFontDatabase
    candidates = [
        "Microsoft YaHei", "微软雅黑",
        "SimHei", "黑体",
        "SimSun", "宋体",
        "KaiTi", "楷体",
    ]
    
    db = QFontDatabase()
    available = set(db.families())
    
    for name in candidates:
        if name in available:
            return name
    
    return ""


class NameDialog(QDialog):
    """宠物命名对话框（与专注商店统一风格）"""
    
    def __init__(self, default_name: str = "我的小宠物", parent=None):
        super().__init__(parent)
        self._cn_font = find_chinese_font()
        self._result = default_name
        self._setup_ui(default_name)
    
    def _setup_ui(self, default_name: str):
        self.setWindowTitle("桌面宠物")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(350, 220)
        
        # 创建圆角容器
        container = QWidget(self)
        container.setGeometry(0, 0, 350, 220)
        container.setStyleSheet("""
            QWidget#container {
                background-color: #FFFDF7;
                border-radius: 20px;
                border: 2px solid #FFE4C4;
            }
        """)
        container.setObjectName("container")
        
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(25, 25, 25, 25)
        
        # 标题
        title = QLabel("🐕 欢迎使用桌面宠物")
        title.setFont(QFont(self._cn_font, 14, QFont.Bold))
        title.setStyleSheet("color: #FF9966; border: none;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # 提示文字
        hint_label = QLabel("请给你的宠物取个名字吧～")
        hint_label.setFont(QFont(self._cn_font, 11))
        hint_label.setStyleSheet("color: #666666; border: none;")
        hint_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(hint_label)
        
        # 输入框
        self._name_input = QLineEdit()
        self._name_input.setText(default_name)
        self._name_input.selectAll()
        self._name_input.setFont(QFont(self._cn_font, 11))
        self._name_input.setFixedHeight(40)
        self._name_input.setStyleSheet("""
            QLineEdit {
                background-color: #FFF5E6;
                border: 2px solid #FFE4C4;
                border-radius: 10px;
                padding: 5px 15px;
                color: #333333;
            }
            QLineEdit:focus {
                border: 2px solid #FFB366;
            }
        """)
        self._name_input.returnPressed.connect(self._on_confirm)
        main_layout.addWidget(self._name_input)
        
        # 按钮行
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.setFont(QFont(self._cn_font, 11))
        cancel_btn.setFixedHeight(36)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                color: #666666;
                border: none;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        # 确认按钮
        confirm_btn = QPushButton("确认")
        confirm_btn.setFont(QFont(self._cn_font, 11))
        confirm_btn.setFixedHeight(36)
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFB366;
                color: white;
                border: none;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #FF9933;
            }
        """)
        confirm_btn.clicked.connect(self._on_confirm)
        button_layout.addWidget(confirm_btn)
        
        main_layout.addLayout(button_layout)
    
    def _on_confirm(self):
        """确认按钮点击"""
        name = self._name_input.text().strip()
        if name:
            self._result = name
            self.accept()
        else:
            self._name_input.setFocus()
    
    def get_name(self) -> str:
        """获取输入的名字"""
        return self._result
    
    def show_center(self):
        """在屏幕中央显示"""
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        return self.exec_()