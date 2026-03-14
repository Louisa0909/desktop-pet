# -*- coding: utf-8 -*-
"""
对话框组件 - 统一商店风格（修复位置问题）
"""
from typing import Optional, Callable, Dict, Any
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QWidget, QFrame,
    QApplication
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QFont

import config


def _get_font() -> QFont:
    """获取字体"""
    from ui.shop_dialog import find_chinese_font
    return QFont(find_chinese_font(), 11)


class BaseDialog(QDialog):
    """基础对话框 - 商店风格"""
    
    def __init__(self, parent, title: str, width: int = 350, height: int = 300):
        super().__init__(parent)
        self._title = title
        self._width = width
        self._height = height
        self._setup_base_ui()
    
    def _setup_base_ui(self):
        """设置基础UI"""
        self.setWindowTitle(self._title)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self._width, self._height)
        
        # 创建圆角容器
        self._container = QWidget(self)
        self._container.setGeometry(0, 0, self._width, self._height)
        self._container.setStyleSheet("""
            QWidget#container {
                background-color: #FFFDF7;
                border-radius: 20px;
                border: 2px solid #FFE4C4;
            }
        """)
        self._container.setObjectName("container")
        
        self._layout = QVBoxLayout(self._container)
        self._layout.setSpacing(15)
        self._layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        self._title_label = QLabel(self._title)
        self._title_label.setFont(QFont(_get_font().family(), 14, QFont.Bold))
        self._title_label.setStyleSheet("color: #FF9966; border: none;")
        self._title_label.setAlignment(Qt.AlignCenter)
        self._layout.addWidget(self._title_label)
    
    def _add_button_row(self, buttons: list):
        """添加按钮行"""
        button_layout = QHBoxLayout()
        
        for text, callback, is_primary in buttons:
            btn = QPushButton(text)
            btn.setFont(_get_font())
            btn.setFixedHeight(36)
            
            if is_primary:
                btn.setStyleSheet("""
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
            else:
                btn.setStyleSheet("""
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
            
            btn.clicked.connect(callback)
            btn.setCursor(Qt.PointingHandCursor)
            button_layout.addWidget(btn)
        
        self._layout.addLayout(button_layout)
    
    def show_near_pet(self, pet_global_pos: QPoint, pet_width: int):
        """
        在宠物附近显示对话框
        
        Args:
            pet_global_pos: 宠物的全局坐标位置
            pet_width: 宠物窗口宽度
        """
        # 获取主屏幕信息
        screen = QApplication.primaryScreen()
        if not screen:
            return
        
        screen_geometry = screen.availableGeometry()
        dialog_w = self._width
        dialog_h = self._height
        
        # 优先放左侧
        x = pet_global_pos.x() - dialog_w - 15
        
        # 左侧放不下，放右侧
        if x < screen_geometry.x():
            x = pet_global_pos.x() + pet_width + 15
        
        # 右侧也超出，贴左边缘
        if x + dialog_w > screen_geometry.x() + screen_geometry.width():
            x = screen_geometry.x() + 10
        
        # 计算y位置（与宠物顶部对齐，稍微偏上）
        y = pet_global_pos.y() - 30
        
        # 确保不超出屏幕上边界
        if y < screen_geometry.y():
            y = screen_geometry.y() + 10
        
        # 确保不超出屏幕下边界
        if y + dialog_h > screen_geometry.y() + screen_geometry.height():
            y = screen_geometry.y() + screen_geometry.height() - dialog_h - 10
        
        self.move(x, y)


class MessageDialog(BaseDialog):
    """发送消息对话框"""
    
    def __init__(self, parent, title: str, on_send: Callable[[str], None]):
        self._on_send = on_send
        super().__init__(parent, title, 350, 250)
        self._finalize()
    
    def _setup_base_ui(self):
        super()._setup_base_ui()
        
        # 消息输入框
        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText("输入要发送的消息...")
        self._text_edit.setMaximumHeight(100)
        self._text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #FFF5E6;
                border: 2px solid #FFE4C4;
                border-radius: 10px;
                padding: 8px;
                font-size: 12px;
            }
            QTextEdit:focus {
                border: 2px solid #FFB366;
            }
        """)
        self._text_edit.setFont(_get_font())
        self._layout.addWidget(self._text_edit)
        
        self._add_button_row([
            ("发送", self._on_send_clicked, True),
            ("取消", self.reject, False)
        ])
    
    def _finalize(self):
        pass
    
    def _on_send_clicked(self):
        message = self._text_edit.toPlainText().strip()
        if message:
            self._on_send(message)
            self.accept()


class UserSelectDialog(BaseDialog):
    """用户选择对话框"""
    
    def __init__(self, parent, title: str, peers: Dict[str, Dict[str, Any]], 
                 on_select: Callable[[str], None]):
        self._peers = peers
        self._on_select = on_select
        super().__init__(parent, title, 380, 350)
        self._finalize()
    
    def _setup_base_ui(self):
        super()._setup_base_ui()
        
        # 说明标签
        label = QLabel("选择要发送消息的用户:")
        label.setFont(_get_font())
        label.setStyleSheet("color: #666666; border: none;")
        self._layout.addWidget(label)
        
        # 用户列表
        self._user_list = QListWidget()
        self._user_list.setStyleSheet("""
            QListWidget {
                background-color: #FFF5E6;
                border: 2px solid #FFE4C4;
                border-radius: 10px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px;
                border-radius: 8px;
            }
            QListWidget::item:selected {
                background-color: #FFB366;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #FFE4C4;
            }
        """)
        self._user_list.setFont(_get_font())
        
        for peer_id, peer_info in self._peers.items():
            item = QListWidgetItem(f"👤 {peer_info.get('name', '未知用户')}")
            item.setData(Qt.UserRole, peer_id)
            self._user_list.addItem(item)
        
        self._user_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._layout.addWidget(self._user_list)
        
        self._add_button_row([
            ("选择", self._on_select_clicked, True),
            ("取消", self.reject, False)
        ])
    
    def _finalize(self):
        pass
    
    def _on_select_clicked(self):
        current = self._user_list.currentItem()
        if current:
            peer_id = current.data(Qt.UserRole)
            self._on_select(peer_id)
            self.accept()
    
    def _on_item_double_clicked(self, item):
        peer_id = item.data(Qt.UserRole)
        self._on_select(peer_id)
        self.accept()


class ChatDialog(BaseDialog):
    """聊天对话框"""
    
    def __init__(self, parent, peer_name: str, on_send_message: Callable[[str], None],
                 on_send_emotion: Callable[[str], None]):
        self._peer_name = peer_name
        self._on_send_message = on_send_message
        self._on_send_emotion = on_send_emotion
        super().__init__(parent, f"与 {peer_name} 聊天", 380, 350)
        self._finalize()
    
    def _setup_base_ui(self):
        super()._setup_base_ui()
        
        # 接收者信息
        receiver_label = QLabel(f"发送给: {self._peer_name}")
        receiver_label.setFont(_get_font())
        receiver_label.setStyleSheet("color: #666666; border: none;")
        self._layout.addWidget(receiver_label)
        
        # 消息输入框
        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText("输入要发送的消息...")
        self._text_edit.setMaximumHeight(100)
        self._text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #FFF5E6;
                border: 2px solid #FFE4C4;
                border-radius: 10px;
                padding: 8px;
                font-size: 12px;
            }
            QTextEdit:focus {
                border: 2px solid #FFB366;
            }
        """)
        self._text_edit.setFont(_get_font())
        self._layout.addWidget(self._text_edit)
        
        # 快捷表情按钮
        emotion_layout = QHBoxLayout()
        quick_emotions = [
            ("😊", "happy"),
            ("😢", "sad"),
            ("❤️", "love"),
            ("😠", "angry"),
            ("🎁", "gift")
        ]
        
        for emoji, emotion in quick_emotions:
            btn = QPushButton(emoji)
            btn.setFixedSize(40, 40)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFF5E6;
                    border: 2px solid #FFE4C4;
                    border-radius: 20px;
                    font-size: 18px;
                }
                QPushButton:hover {
                    background-color: #FFB366;
                    border: 2px solid #FFB366;
                }
            """)
            btn.clicked.connect(lambda checked, e=emotion: self._send_emotion(e))
            btn.setCursor(Qt.PointingHandCursor)
            emotion_layout.addWidget(btn)
        
        self._layout.addLayout(emotion_layout)
        
        self._add_button_row([
            ("发送消息", self._send_message, True),
            ("取消", self.reject, False)
        ])
    
    def _finalize(self):
        pass
    
    def _send_message(self):
        message = self._text_edit.toPlainText().strip()
        if message:
            self._on_send_message(message)
            self.accept()
    
    def _send_emotion(self, emotion: str):
        self._on_send_emotion(emotion)
        self.accept()


class DebugDialog(BaseDialog):
    """调试信息对话框"""
    
    def __init__(self, parent, title: str, get_info: Callable[[], Dict[str, Any]]):
        self._get_info = get_info
        super().__init__(parent, title, 420, 380)
        self._finalize()
        self._refresh()
    
    def _setup_base_ui(self):
        super()._setup_base_ui()
        
        # 信息显示区域
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #FFF5E6;
                border: 2px solid #FFE4C4;
                border-radius: 10px;
                padding: 10px;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
        """)
        self._layout.addWidget(self._text_edit)
        
        self._add_button_row([
            ("刷新", self._refresh, False),
            ("关闭", self.accept, True)
        ])
    
    def _finalize(self):
        pass
    
    def _refresh(self):
        info = self._get_info()
        self._text_edit.setText(self._format_info(info))
    
    def _format_info(self, info: Dict[str, Any]) -> str:
        lines = ["╔══════════════════════════════╗"]
        lines.append("║      网络调试信息            ║")
        lines.append("╠══════════════════════════════╣")
        
        status = "✓ 运行中" if info.get('network_available') else "✗ 不可用"
        lines.append(f"║ 网络状态: {status:<17}║")
        lines.append(f"║ 本地IP:   {info.get('local_ip', '未知'):<17}║")
        lines.append(f"║ 宠物ID:   {info.get('pet_id', '未知'):<17}║")
        lines.append(f"║ 宠物名称: {info.get('pet_name', '未知'):<17}║")
        lines.append(f"║ TCP连接:  {info.get('tcp_connections', 0):<17}║")
        lines.append("╠══════════════════════════════╣")
        lines.append(f"║ 在线用户: {info.get('online_count', 0)} 人{' ' * 17}║")
        
        for peer in info.get('peers', []):
            name = peer.get('name', '未知')[:12]
            lines.append(f"║   · {name}{' ' * (23 - len(name))}║")
        
        lines.append("╚══════════════════════════════╝")
        
        return '\n'.join(lines)


class DialogFactory:
    """对话框工厂"""
    
    def __init__(self, parent):
        self._parent = parent
    
    def _get_pet_global_pos(self) -> QPoint:
        """获取宠物的全局位置"""
        return self._parent.mapToGlobal(QPoint(0, 0))
    
    def show_message_dialog(self, title: str, on_send: Callable[[str], None]) -> bool:
        dialog = MessageDialog(self._parent, title, on_send)
        dialog.show_near_pet(self._get_pet_global_pos(), self._parent.width())
        return dialog.exec_() == QDialog.Accepted
    
    def show_user_select(self, title: str, peers: Dict[str, Dict[str, Any]],
                         on_select: Callable[[str], None]) -> bool:
        dialog = UserSelectDialog(self._parent, title, peers, on_select)
        dialog.show_near_pet(self._get_pet_global_pos(), self._parent.width())
        return dialog.exec_() == QDialog.Accepted
    
    def show_chat_dialog(self, peer_name: str, on_send_message: Callable[[str], None],
                         on_send_emotion: Callable[[str], None]) -> bool:
        dialog = ChatDialog(self._parent, peer_name, on_send_message, on_send_emotion)
        dialog.show_near_pet(self._get_pet_global_pos(), self._parent.width())
        return dialog.exec_() == QDialog.Accepted
    
    def show_debug_dialog(self, title: str, get_info: Callable[[], Dict[str, Any]]):
        dialog = DebugDialog(self._parent, title, get_info)
        dialog.show_near_pet(self._get_pet_global_pos(), self._parent.width())
        dialog.exec_()