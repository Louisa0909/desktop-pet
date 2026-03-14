# -*- coding: utf-8 -*-
"""
右键菜单（含复习提纲功能）
"""
from PyQt5.QtWidgets import QMenu, QAction

from core.mood_manager import MoodManager
from ui.dialogs import DialogFactory
import config


class ContextMenu(QMenu):
    """右键菜单"""
    
    def __init__(self, pet):
        super().__init__()
        self._pet = pet
        self._dialog_factory = DialogFactory(pet)
        
        self._build_menu()
    
    def _build_menu(self):
        """构建菜单"""
        self._add_focus_info()
        self._add_study_menu()  # 新增：复习提纲
        self._add_mood_menu()
        self._add_network_menu()
        self._add_quit_action()
    
    def _add_focus_info(self):
        """显示当前专注时长"""
        if hasattr(self._pet, '_focus_manager') and self._pet._focus_manager.focus_seconds > 0:
            minutes = self._pet._focus_manager.focus_seconds // 60
            info_action = QAction(f"📊 当前专注: {minutes} 分钟", self)
            info_action.setEnabled(False)
            self.addAction(info_action)
            self.addSeparator()
    
    def _add_study_menu(self):
        """添加学习相关菜单"""
        study_menu = self.addMenu("📚 学习工具")
        
        # 复习提纲
        outline_action = QAction("📝 复习提纲生成器", self)
        outline_action.triggered.connect(self._open_upload_dialog)
        study_menu.addAction(outline_action)
        
        self.addSeparator()
    
    def _add_mood_menu(self):
        """添加表情菜单"""
        mood_menu = self.addMenu("😊 切换表情")
        
        for mood in self._pet.get_available_moods():
            action = QAction(config.EMOTION_NAMES.get(mood, mood), self)
            action.triggered.connect(lambda checked, m=mood: self._pet.set_mood(m))
            mood_menu.addAction(action)
        
        self.addSeparator()
    
    def _add_network_menu(self):
        """添加网络菜单"""
        if not hasattr(self._pet, '_network_manager') or not self._pet._network_manager:
            return
        
        network_menu = self.addMenu("🌐 网络功能")
        
        online_count = self._pet.online_count
        status_action = QAction(f"在线用户: {online_count} 人", self)
        status_action.setEnabled(False)
        network_menu.addAction(status_action)
        
        network_menu.addSeparator()
        
        self._add_emotion_broadcast_menu(network_menu)
        
        message_action = QAction("💬 发送消息给所有人", self)
        message_action.triggered.connect(self._show_broadcast_message_dialog)
        network_menu.addAction(message_action)
        
        if self._pet.online_count > 0:
            self._add_user_menu(network_menu)
        
        network_menu.addSeparator()
        
        debug_action = QAction("🔧 网络调试", self)
        debug_action.triggered.connect(self._show_debug_dialog)
        network_menu.addAction(debug_action)
        
        self.addSeparator()
    
    def _add_emotion_broadcast_menu(self, parent_menu: QMenu):
        emotion_menu = parent_menu.addMenu("😊 发送表情给所有人")
        
        for emotion, name in config.EMOTION_NAMES.items():
            action = QAction(name, self)
            action.triggered.connect(
                lambda checked, e=emotion: self._pet.send_emotion_to_all(e)
            )
            emotion_menu.addAction(action)
    
    def _add_user_menu(self, parent_menu: QMenu):
        send_to_menu = parent_menu.addMenu("📤 发送给用户")
        
        for peer_id, peer_info in self._pet.online_peers.items():
            user_action = QAction(f"👤 {peer_info.get('name', '未知用户')}", self)
            user_action.triggered.connect(
                lambda checked, pid=peer_id: self._show_user_chat_dialog(pid)
            )
            send_to_menu.addAction(user_action)
    
    def _add_quit_action(self):
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._quit)
        self.addAction(quit_action)
    
    def _open_upload_dialog(self):
        """打开复习提纲对话框"""
        if hasattr(self._pet, '_open_upload_dialog'):
            self._pet._open_upload_dialog()
    
    def _show_broadcast_message_dialog(self):
        self._dialog_factory.show_message_dialog(
            "发送消息给所有人",
            lambda msg: self._pet.send_message_to_all(msg)
        )
    
    def _show_user_chat_dialog(self, peer_id: str):
        peer_info = self._pet.online_peers.get(peer_id)
        if not peer_info:
            return
        
        peer_name = peer_info.get('name', '未知用户')
        
        self._dialog_factory.show_chat_dialog(
            peer_name,
            lambda msg: self._pet.send_message_to_user(msg, peer_id, peer_name),
            lambda emotion: self._pet.send_emotion_to_user(emotion, peer_id, peer_name)
        )
    
    def _show_debug_dialog(self):
        self._dialog_factory.show_debug_dialog(
            "网络调试信息",
            self._pet.get_network_info
        )
    
    def _quit(self):
        from PyQt5.QtWidgets import QApplication
        self._pet.cleanup()
        QApplication.quit()