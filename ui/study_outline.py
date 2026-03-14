#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
复习提纲生成器 - 文件上传对话框（风格与专注商店统一）
"""

import os
import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QWidget,
    QLabel, QTextEdit, QFileDialog, QMessageBox,
    QProgressBar, QScrollArea, QApplication, QLineEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt5.QtGui import QFont

import requests
import config


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


class LLMWorker(QThread):
    """后台线程调用 LLM API，避免阻塞 UI"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, content, parent=None):
        super().__init__(parent)
        self.content = content

    def run(self):
        try:
            self.progress.emit(50)

            url = config.LLM_API_URL
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.LLM_API_KEY}"
            }
            data = {
                "model": config.LLM_MODEL,
                "messages": [
                    {"role": "system", "content": "你是一个有用的助手，擅长总结学习材料并生成复习提纲。"},
                    {"role": "user", "content": f"附件是我的学习材料，根据附件快速简洁地生成一份复习提纲。\n\n学习材料内容：\n{self.content}"}
                ]
            }

            response = requests.post(url, headers=headers, json=data, timeout=120)
            self.progress.emit(80)

            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    self.finished.emit(result["choices"][0]["message"]["content"])
                else:
                    self.error.emit("API 返回结果为空")
            else:
                error_msg = f"API调用失败，状态码：{response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f"\n错误详情：{json.dumps(error_detail, ensure_ascii=False)}"
                except Exception:
                    pass
                self.error.emit(error_msg)

        except requests.exceptions.Timeout:
            self.error.emit("API调用超时，请稍后重试")
        except Exception as e:
            self.error.emit(f"调用API时出错：{str(e)}")


class FileUploadDialog(QDialog):
    """文件上传对话框（与专注商店统一风格）"""

    dialog_closed = pyqtSignal()

    def __init__(self, parent=None, font_family: str = "", on_focus_start=None):
        super().__init__(parent)
        self.selected_file = None
        self.file_content = None
        self._font_family = font_family or find_chinese_font()
        self._worker = None
        self._on_focus_start = on_focus_start
        self.init_ui()

    def init_ui(self):
        """初始化UI - 与专注商店统一风格"""
        self.setWindowTitle("复习提纲生成器")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(600, 700)

        # 圆角容器
        container = QWidget(self)
        container.setGeometry(0, 0, 600, 700)
        container.setObjectName("container")
        container.setStyleSheet("""
            QWidget#container {
                background-color: #FFFDF7;
                border-radius: 20px;
                border: 2px solid #FFE4C4;
            }
        """)

        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title = QLabel("📚 复习提纲")
        title.setFont(QFont(self._font_family, 16, QFont.Bold))
        title.setStyleSheet("color: #FF9966; border: none;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # 文件选择区域
        file_label = QLabel("请选择学习材料（PDF或Word文档）：")
        file_label.setFont(QFont(self._font_family, 11))
        file_label.setStyleSheet("color: #666666; border: none;")
        main_layout.addWidget(file_label)

        # 文件选择按钮
        self.file_btn = QPushButton("选择文件")
        self.file_btn.setFont(QFont(self._font_family, 11))
        self.file_btn.setFixedHeight(36)
        self.file_btn.setCursor(Qt.PointingHandCursor)
        self.file_btn.setStyleSheet("""
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
        self.file_btn.clicked.connect(self.select_file)
        main_layout.addWidget(self.file_btn)

        # 显示选中的文件
        self.file_info_label = QLabel("未选择文件")
        self.file_info_label.setFont(QFont(self._font_family, 10))
        self.file_info_label.setStyleSheet("color: #999999; border: none;")
        main_layout.addWidget(self.file_info_label)

        # 生成按钮
        self.generate_btn = QPushButton("生成复习提纲")
        self.generate_btn.setFont(QFont(self._font_family, 11))
        self.generate_btn.setFixedHeight(36)
        self.generate_btn.setEnabled(False)
        self.generate_btn.setCursor(Qt.PointingHandCursor)
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9966;
                color: white;
                border: none;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #FF8844;
            }
            QPushButton:disabled {
                background-color: #DDDDDD;
            }
        """)
        self.generate_btn.clicked.connect(self.generate_outline)
        main_layout.addWidget(self.generate_btn)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #FFE4C4;
                border-radius: 5px;
                text-align: center;
                background-color: #FFF5E6;
            }
            QProgressBar::chunk {
                background-color: #FFB366;
            }
        """)
        main_layout.addWidget(self.progress_bar)

        # 结果标签
        result_label = QLabel("复习提纲：")
        result_label.setFont(QFont(self._font_family, 11))
        result_label.setStyleSheet("color: #666666; font-weight: bold; border: none;")
        main_layout.addWidget(result_label)

        # 文本显示区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
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

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("生成的复习提纲将显示在这里...")
        self.result_text.setStyleSheet("""
            QTextEdit {
                background-color: #FFF5E6;
                border: none;
                border-radius: 10px;
                padding: 15px;
                font-size: 15px;
            }
        """)
        self.result_text.setFont(QFont(self._font_family, 11))
        scroll_area.setWidget(self.result_text)
        main_layout.addWidget(scroll_area)

        # 按钮行
        button_layout = QHBoxLayout()
        
        # 复制按钮
        copy_btn = QPushButton("复制内容")
        copy_btn.setFont(QFont(self._font_family, 11))
        copy_btn.setFixedHeight(36)
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setStyleSheet("""
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
        copy_btn.clicked.connect(self._copy_content)
        button_layout.addWidget(copy_btn)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setFont(QFont(self._font_family, 11))
        close_btn.setFixedHeight(36)
        close_btn.setCursor(Qt.PointingHandCursor)
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
        button_layout.addWidget(close_btn)
        
        main_layout.addLayout(button_layout)

    def _copy_content(self):
        """复制内容到剪贴板"""
        text = self.result_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, "提示", "已复制到剪贴板")

    def showEvent(self, event):
        """显示时触发专注状态"""
        super().showEvent(event)
        if self._on_focus_start:
            self._on_focus_start()

    def closeEvent(self, event):
        """关闭时发出信号"""
        self.dialog_closed.emit()
        super().closeEvent(event)

    def reject(self):
        """关闭时发出信号"""
        self.dialog_closed.emit()
        super().reject()

    def select_file(self):
        """选择文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择学习材料",
            "",
            "支持的文件 (*.pdf *.docx *.doc);;PDF文件 (*.pdf);;Word文档 (*.docx *.doc)"
        )
        if file_path:
            self.selected_file = file_path
            self.file_info_label.setText(f"已选择: {os.path.basename(file_path)}")
            self.file_info_label.setStyleSheet("color: #4CAF50; border: none;")
            self.generate_btn.setEnabled(True)

    def generate_outline(self):
        """生成复习提纲"""
        if not self.selected_file:
            QMessageBox.warning(self, "警告", "请先选择文件！")
            return

        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            self.result_text.setText("正在读取文件...")
            self.generate_btn.setEnabled(False)
            QApplication.processEvents()

            file_ext = os.path.splitext(self.selected_file)[1].lower()
            if file_ext == '.pdf':
                self.file_content = self._read_pdf(self.selected_file)
            elif file_ext in ['.doc', '.docx']:
                self.file_content = self._read_word(self.selected_file)
            else:
                QMessageBox.warning(self, "警告", "不支持的文件格式！")
                self._reset_ui()
                return

            if not self.file_content:
                self._reset_ui()
                return

            self.progress_bar.setValue(30)
            self.result_text.setText("正在调用大语言模型生成复习提纲，请耐心等待...")
            QApplication.processEvents()

            self._worker = LLMWorker(self.file_content)
            self._worker.progress.connect(self.progress_bar.setValue)
            self._worker.finished.connect(self._on_llm_finished)
            self._worker.error.connect(self._on_llm_error)
            self._worker.start()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成复习提纲时出错：{str(e)}")
            self._reset_ui()

    def _on_llm_finished(self, outline):
        """LLM 调用完成"""
        self.progress_bar.setValue(100)
        self.result_text.setMarkdown(outline)
        self.generate_btn.setEnabled(True)

    def _on_llm_error(self, error_msg):
        """LLM 调用出错"""
        QMessageBox.warning(self, "生成失败", error_msg)
        self._reset_ui()

    def _reset_ui(self):
        """重置 UI 状态"""
        self.progress_bar.setVisible(False)
        self.generate_btn.setEnabled(True)

    def _read_pdf(self, file_path):
        """读取PDF文件内容"""
        try:
            import PyPDF2
            content = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
            return content
        except ImportError:
            QMessageBox.warning(self, "警告", "未安装 PyPDF2 库，请先安装：pip install PyPDF2")
            return None
        except Exception as e:
            QMessageBox.warning(self, "警告", f"读取PDF文件失败：{str(e)}")
            return None

    def _read_word(self, file_path):
        """读取Word文件内容"""
        try:
            import docx
            doc = docx.Document(file_path)
            content = ""
            for paragraph in doc.paragraphs:
                content += paragraph.text + "\n"
            return content
        except ImportError:
            QMessageBox.warning(self, "警告", "未安装 python-docx 库，请先安装：pip install python-docx")
            return None
        except Exception as e:
            QMessageBox.warning(self, "警告", f"读取Word文件失败：{str(e)}")
            return None

    def show_near_pet(self, pet_pos: QPoint, pet_width: int):
        """在宠物附近显示对话框"""
        screen = QApplication.primaryScreen().geometry()
        dialog_w = self.width()
        dialog_h = self.height()
        
        # 优先放左侧
        x = pet_pos.x() - dialog_w - 10
        if x < screen.x():
            x = pet_pos.x() + pet_width + 10
        
        if x + dialog_w > screen.x() + screen.width():
            x = screen.x()
        
        y = pet_pos.y() - 100
        y = max(screen.y(), min(y, screen.y() + screen.height() - dialog_h))
        
        self.move(x, y)