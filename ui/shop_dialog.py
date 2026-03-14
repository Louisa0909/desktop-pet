# -*- coding: utf-8 -*-
"""
商店对话框 - 皮肤商店和统计显示（支持角色分区和皮肤等级系统）
"""
import os
import re
from typing import Optional, TYPE_CHECKING
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QWidget, QLabel, QPushButton, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QFont, QPixmap, QColor, QPainter, QFontDatabase

import config

if TYPE_CHECKING:
    from utils.userdata import UserDataManager


def find_chinese_font() -> str:
    """检测系统中可用的中文字体"""
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


def parse_skin_level(skin_name: str) -> int:
    """从皮肤文件名解析等级，如 lv0-1.png -> 0, lv1.png -> 1, lv2.png -> 2"""
    base = os.path.splitext(skin_name)[0]
    m = re.match(r'^lv(\d+)', base)
    if m:
        return int(m.group(1))
    return 0


def get_skin_type(skin_name: str) -> str:
    """获取皮肤类型: normal, english, coding"""
    base = os.path.splitext(skin_name)[0]
    if base.startswith("lvEn"):
        return "english"
    if base.startswith("lvpy"):
        return "coding"
    return "normal"


class ShopDialog(QDialog):
    """专注商店对话框（支持角色分区和皮肤等级系统）"""
    
    CHARACTER_NAMES = {
        "cat": "Cat",
        "cheems": "Cheems",
    }
    
    # 类级别缓存（跨实例共享）
    _shared_pixmap_cache = {}
    _shared_gray_cache = {}
    
    def __init__(self, user_data: 'UserDataManager', on_skin_selected: callable,
                 on_character_changed: callable = None, parent=None):
        super().__init__(parent)
        
        self._user_data = user_data
        self._on_skin_selected = on_skin_selected
        self._on_character_changed = on_character_changed
        self._cn_font = find_chinese_font()
        self._skin_pixmap_cache = {}
        
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWindowTitle("专注商店")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 650)
        
        # 创建圆角容器
        container = QWidget(self)
        container.setGeometry(0, 0, 420, 650)
        container.setStyleSheet("""
            QWidget#container {
                background-color: #FFFDF7;
                border-radius: 20px;
                border: 2px solid #FFE4C4;
            }
        """)
        container.setObjectName("container")
        
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 16, 20, 16)
        
        # 标题
        title = QLabel("🏪 专注商店")
        title.setFont(QFont(self._cn_font, 16, QFont.Bold))
        title.setStyleSheet("color: #FF9966; border: none;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # 统计信息栏
        stats_frame = self._create_stats_frame()
        main_layout.addWidget(stats_frame)
        
        # 等级说明
        level_hint = QLabel("💡 lv0可直接购买 | lvN需最高单次专注达N分钟 | lvEn/lvpy需累计分类专注时长")
        level_hint.setFont(QFont(self._cn_font, 8))
        level_hint.setStyleSheet("color: #999999; border: none;")
        level_hint.setAlignment(Qt.AlignCenter)
        level_hint.setWordWrap(True)
        main_layout.addWidget(level_hint)
        
        # 皮肤商店区域（滚动）
        scroll = self._create_skins_scroll()
        main_layout.addWidget(scroll)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setFont(QFont(self._cn_font, 11))
        close_btn.setFixedHeight(36)
        close_btn.setStyleSheet("""
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
        close_btn.clicked.connect(self.reject)
        close_btn.setCursor(Qt.PointingHandCursor)
        main_layout.addWidget(close_btn)
    
    def _create_stats_frame(self) -> QFrame:
        """创建统计信息栏"""
        stats_frame = QFrame()
        stats_frame.setStyleSheet("background-color: #FFF5E6; border-radius: 10px;")
        stats_layout = QVBoxLayout(stats_frame)
        stats_layout.setContentsMargins(15, 8, 15, 8)
        stats_layout.setSpacing(4)
        
        # 第一行：今日/最高专注 + 存币
        row1 = QHBoxLayout()
        focus_info = QLabel(f"今日: {self._user_data.get_daily_focus_formatted()} | 最高: {self._user_data.get_max_focus_formatted()}")
        focus_info.setFont(QFont(self._cn_font, 10))
        focus_info.setStyleSheet("color: #666666; border: none;")
        row1.addWidget(focus_info)
        row1.addStretch()
        self._coins_display = QLabel(f"💰 {self._user_data.total_coins}")
        self._coins_display.setFont(QFont(self._cn_font, 11))
        self._coins_display.setStyleSheet("color: #FF9933; font-weight: bold; border: none;")
        row1.addWidget(self._coins_display)
        stats_layout.addLayout(row1)
        
        # 第二行：英语/代码累计专注
        row2 = QHBoxLayout()
        en_info = QLabel(f"📖 英语: {self._user_data.get_english_focus_formatted()}")
        en_info.setFont(QFont(self._cn_font, 9))
        en_info.setStyleSheet("color: #5B9BD5; border: none;")
        row2.addWidget(en_info)
        row2.addStretch()
        py_info = QLabel(f"💻 代码: {self._user_data.get_coding_focus_formatted()}")
        py_info.setFont(QFont(self._cn_font, 9))
        py_info.setStyleSheet("color: #70AD47; border: none;")
        row2.addWidget(py_info)
        stats_layout.addLayout(row2)
        
        return stats_frame
    
    def _create_skins_scroll(self) -> QScrollArea:
        """创建皮肤滚动区域"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                width: 8px;
                background: #F0F0F0;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #FFB366;
                border-radius: 4px;
            }
        """)
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        self._main_scroll_layout = QVBoxLayout(scroll_content)
        self._main_scroll_layout.setSpacing(8)
        self._main_scroll_layout.setContentsMargins(5, 5, 5, 5)
        
        # 加载 cat 角色区域
        self._load_character_section("cat")
        
        # 加载 cheems 角色区域
        self._load_character_section("cheems")
        
        self._main_scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        return scroll
    
    def _load_character_section(self, character: str):
        """加载一个角色的皮肤区域"""
        is_cheems = (character == "cheems")
        cheems_unlocked = self._user_data.check_cheems_unlock()
        
        # 角色标题
        header_layout = QHBoxLayout()
        
        char_name = self.CHARACTER_NAMES.get(character, character)
        if is_cheems and not cheems_unlocked:
            header_text = f"🔒 {char_name}（最高专注达{config.CHEEMS_UNLOCK_MINUTES}分钟解锁）"
            header_color = "#AAAAAA"
        else:
            is_current = (self._user_data.current_character == character)
            current_tag = " ✅" if is_current else ""
            header_text = f"🐾 {char_name}{current_tag}"
            header_color = "#FF9966"
        
        header_label = QLabel(header_text)
        header_label.setFont(QFont(self._cn_font, 11, QFont.Bold))
        header_label.setStyleSheet(f"color: {header_color}; border: none;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        self._main_scroll_layout.addLayout(header_layout)
        
        # 分割线
        line = QFrame()
        line.setFixedHeight(1)
        if is_cheems and not cheems_unlocked:
            line.setStyleSheet("background-color: #DDDDDD;")
        else:
            line.setStyleSheet("background-color: #FFE4C4;")
        self._main_scroll_layout.addWidget(line)
        
        # 皮肤网格
        skins = self._get_character_skins(character)
        
        grid_widget = QWidget()
        grid_widget.setStyleSheet("background-color: transparent;")
        grid = QGridLayout(grid_widget)
        grid.setSpacing(10)
        grid.setContentsMargins(5, 5, 5, 5)
        
        if not skins:
            empty_label = QLabel("暂无皮肤")
            empty_label.setFont(QFont(self._cn_font, 10))
            empty_label.setStyleSheet("color: #CCCCCC; border: none;")
            empty_label.setAlignment(Qt.AlignCenter)
            grid.addWidget(empty_label, 0, 0, 1, 3)
        else:
            for i, skin_file in enumerate(skins):
                row = i // 3
                col = i % 3
                # skin_path 包含角色子目录，如 "cat/lv0-1.png"
                skin_path = f"{character}/{skin_file}"
                locked = is_cheems and not cheems_unlocked
                card = self._create_skin_card(skin_path, skin_file, character, locked)
                grid.addWidget(card, row, col)
        
        self._main_scroll_layout.addWidget(grid_widget)
    
    def _get_character_skins(self, character: str) -> list:
        """获取某个角色的皮肤文件列表"""
        skins = []
        char_dir = config.get_resource_path(config.SKINS_DIR, character)
        
        if os.path.exists(char_dir):
            for f in os.listdir(char_dir):
                if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                    skins.append(f)
        
        # 排序：普通等级皮肤先按等级排，然后是特殊皮肤
        def sort_key(s):
            skin_type = get_skin_type(s)
            if skin_type == "normal":
                return (0, parse_skin_level(s), s)
            elif skin_type == "english":
                return (1, 0, s)
            else:
                return (2, 0, s)
        
        skins.sort(key=sort_key)
        return skins
    
    def _create_skin_card(self, skin_path: str, skin_file: str, character: str, character_locked: bool) -> QFrame:
        """创建皮肤卡片（支持角色系统和分类解锁）"""
        card = QFrame()
        card.setFixedSize(115, 150)
        
        skin_type = get_skin_type(skin_file)
        level = parse_skin_level(skin_file)
        is_owned = self._user_data.is_skin_owned(skin_path)
        is_unlocked = (not character_locked) and self._user_data.is_skin_unlocked(skin_file, level)
        
        # 根据状态设置样式
        if character_locked:
            card.setStyleSheet("""
                QFrame {
                    background-color: #EEEEEE;
                    border-radius: 10px;
                    border: 2px solid #CCCCCC;
                }
            """)
        elif is_owned or is_unlocked:
            card.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border-radius: 10px;
                    border: 2px solid #FFE4C4;
                }
                QFrame:hover {
                    border: 2px solid #FFB366;
                }
            """)
        else:
            card.setStyleSheet("""
                QFrame {
                    background-color: #F5F5F5;
                    border-radius: 10px;
                    border: 2px solid #DDDDDD;
                }
                QFrame:hover {
                    border: 2px solid #BBBBBB;
                }
            """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(2)
        layout.setContentsMargins(5, 4, 5, 4)
        
        # 类型/等级标签
        lv_label = QLabel()
        lv_label.setFont(QFont(self._cn_font, 8))
        lv_label.setAlignment(Qt.AlignCenter)
        lv_label.setStyleSheet("border: none;")
        
        if skin_type == "english":
            lv_label.setText("📖 英语")
            if character_locked or not is_unlocked:
                lv_label.setStyleSheet("color: #AAAAAA; border: none; font-weight: bold;")
            else:
                lv_label.setStyleSheet("color: #5B9BD5; border: none; font-weight: bold;")
        elif skin_type == "coding":
            lv_label.setText("💻 代码")
            if character_locked or not is_unlocked:
                lv_label.setStyleSheet("color: #AAAAAA; border: none; font-weight: bold;")
            else:
                lv_label.setStyleSheet("color: #70AD47; border: none; font-weight: bold;")
        else:
            lv_label.setText(f"Lv{level}")
            if character_locked:
                lv_label.setStyleSheet("color: #AAAAAA; border: none; font-weight: bold;")
            elif level == 0:
                lv_label.setStyleSheet("color: #66BB6A; border: none; font-weight: bold;")
            elif is_owned or is_unlocked:
                lv_label.setStyleSheet("color: #FF9933; border: none; font-weight: bold;")
            else:
                lv_label.setStyleSheet("color: #AAAAAA; border: none; font-weight: bold;")
        
        layout.addWidget(lv_label)
        
        # 图片
        img_label = QLabel()
        img_label.setFixedSize(80, 80)
        img_label.setAlignment(Qt.AlignCenter)
        img_label.setStyleSheet("border: none;")
        
        pixmap = self._get_skin_pixmap(skin_path)
        if pixmap:
            if character_locked or (not is_owned and not is_unlocked):
                pixmap = self._get_gray_pixmap(skin_path, pixmap)
            img_label.setPixmap(pixmap)
        
        layout.addWidget(img_label, alignment=Qt.AlignCenter)
        
        # 价格/状态标签
        price_label = QLabel()
        price_label.setFont(QFont(self._cn_font, 8))
        price_label.setAlignment(Qt.AlignCenter)
        price_label.setStyleSheet("border: none;")
        
        if character_locked:
            price_label.setText("🔒 未解锁")
            price_label.setStyleSheet("color: #AAAAAA; border: none;")
        elif is_owned:
            if self._user_data.today_skin == skin_path:
                price_label.setText("使用中")
                price_label.setStyleSheet("color: #4CAF50; border: none; font-weight: bold;")
            else:
                price_label.setText("已拥有")
                price_label.setStyleSheet("color: #4CAF50; border: none;")
        elif not is_unlocked:
            price_label.setText(self._get_unlock_hint(skin_file, skin_type, level))
            price_label.setStyleSheet("color: #AAAAAA; border: none;")
        else:
            price_label.setText(f"{config.SKIN_PRICE}币")
            price_label.setStyleSheet("color: #FF9933; border: none;")
        
        layout.addWidget(price_label)
        
        # 点击事件
        if not character_locked:
            card.setCursor(Qt.PointingHandCursor)
            card.mousePressEvent = lambda e, sp=skin_path, sf=skin_file, st=skin_type, lv=level, ch=character, pl=price_label: \
                self._on_skin_click(sp, sf, st, lv, ch, pl)
        
        return card
    
    def _get_unlock_hint(self, skin_file: str, skin_type: str, level: int) -> str:
        """获取未解锁提示文字"""
        if skin_type == "english":
            en_min = self._user_data.english_focus_seconds // 60
            return f"英语{en_min}/{config.ENGLISH_SKIN_UNLOCK_MINUTES}m"
        elif skin_type == "coding":
            py_min = self._user_data.coding_focus_seconds // 60
            return f"代码{py_min}/{config.CODING_SKIN_UNLOCK_MINUTES}m"
        else:
            return f"需{level}分钟专注"
    
    def _get_skin_pixmap(self, skin_path: str) -> Optional[QPixmap]:
        """获取皮肤图片（类级别缓存）"""
        if skin_path in ShopDialog._shared_pixmap_cache:
            return ShopDialog._shared_pixmap_cache[skin_path]
        
        full_path = config.get_resource_path(config.SKINS_DIR, skin_path)
        if not os.path.exists(full_path):
            return None
        
        pixmap = QPixmap(full_path)
        if pixmap.isNull():
            return None
        
        pixmap = pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        ShopDialog._shared_pixmap_cache[skin_path] = pixmap
        return pixmap
    
    def _get_gray_pixmap(self, skin_path: str, pixmap: QPixmap) -> QPixmap:
        """获取灰度皮肤图片（类级别缓存）"""
        if skin_path in ShopDialog._shared_gray_cache:
            return ShopDialog._shared_gray_cache[skin_path]
        
        gray_pixmap = QPixmap(pixmap.size())
        gray_pixmap.fill(Qt.transparent)
        painter = QPainter(gray_pixmap)
        painter.setOpacity(0.4)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        
        ShopDialog._shared_gray_cache[skin_path] = gray_pixmap
        return gray_pixmap
    
    def _on_skin_click(self, skin_path: str, skin_file: str, skin_type: str, level: int, character: str, price_label: QLabel):
        """点击皮肤卡片"""
        if self._user_data.is_skin_owned(skin_path):
            # 已拥有，使用（并切换角色）
            self._user_data.today_skin = skin_path
            self._user_data.current_character = character
            self._user_data.save(force=True)
            
            price_label.setText("使用中")
            price_label.setStyleSheet("color: #4CAF50; border: none; font-weight: bold;")
            
            self._on_skin_selected(skin_path)
            if self._on_character_changed:
                self._on_character_changed(character)
            
            self.reject()
        else:
            # 检查解锁条件
            if not self._user_data.is_skin_unlocked(skin_file, level):
                if skin_type == "english":
                    en_min = self._user_data.english_focus_seconds // 60
                    price_label.setText(f"英语{en_min}/{config.ENGLISH_SKIN_UNLOCK_MINUTES}m")
                elif skin_type == "coding":
                    py_min = self._user_data.coding_focus_seconds // 60
                    price_label.setText(f"代码{py_min}/{config.CODING_SKIN_UNLOCK_MINUTES}m")
                else:
                    best_min = self._user_data.max_focus_seconds // 60
                    price_label.setText(f"最高{best_min}/{level}分钟")
                price_label.setStyleSheet("color: #FF6B6B; border: none;")
                return
            
            # 检查存币
            if self._user_data.total_coins >= config.SKIN_PRICE:
                self._user_data.spend_coins(config.SKIN_PRICE)
                self._user_data.own_skin(skin_path)
                self._user_data.today_skin = skin_path
                self._user_data.current_character = character
                self._user_data.save(force=True)
                
                self._coins_display.setText(f"💰 {self._user_data.total_coins}")
                price_label.setText("使用中")
                price_label.setStyleSheet("color: #4CAF50; border: none; font-weight: bold;")
                
                self._on_skin_selected(skin_path)
                if self._on_character_changed:
                    self._on_character_changed(character)
                
                print(f"[商店] 购买皮肤: {skin_path}")
            else:
                price_label.setText(f"存币不足({self._user_data.total_coins}/{config.SKIN_PRICE})")
                price_label.setStyleSheet("color: #FF6B6B; border: none;")
    
    def show_near_pet(self, pet_pos: QPoint, pet_width: int):
        """在宠物附近显示对话框"""
        screen = self.screen().geometry()
        dialog_w = self.width()
        dialog_h = self.height()
        
        x = pet_pos.x() - dialog_w - 10
        if x < screen.x():
            x = pet_pos.x() + pet_width + 10
        
        if x + dialog_w > screen.x() + screen.width():
            x = screen.x()
        
        y = pet_pos.y() - 100
        y = max(screen.y(), min(y, screen.y() + screen.height() - dialog_h))
        
        self.move(x, y)
