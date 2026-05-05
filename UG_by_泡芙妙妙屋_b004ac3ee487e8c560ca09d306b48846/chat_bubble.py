"""
对话气泡 UI 组件
显示宠物对话内容
"""

import math
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal as Signal, QRectF
from PyQt6.QtWidgets import (
    QWidget, QGraphicsDropShadowEffect, QLabel, QTextEdit,
    QPushButton, QHBoxLayout, QVBoxLayout
)
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QPainterPath,
    QFontMetrics, QIcon
)
from PyQt6.QtCore import pyqtSignal as Signal


class ChatBubble(QWidget):
    """对话气泡组件"""

    # 信号：用户发送消息
    message_sent = Signal(str)
    # 信号：气泡请求关闭
    close_requested = Signal()
    # 信号：开始输入（显示思考状态）
    thinking_started = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._target_width = 320
        self._target_height = 180
        self.setFixedSize(self._target_width, self._target_height)

        # 气泡颜色配置
        self.bg_color = QColor(255, 255, 255, 245)
        self.border_color = QColor(220, 200, 230, 200)
        self.text_color = QColor(60, 50, 70, 255)
        self.accent_color = QColor(255, 182, 193, 255)  # 粉色主题

        # 状态
        self.is_thinking = False
        self.current_text = ""
        self.display_text = ""
        self.typing_index = 0
        self.typing_timer: Optional[QTimer] = None

        # UI 元素初始化将在 showEvent 中完成
        self._setup_ui()

        # 动画
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(300)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _setup_ui(self):
        """设置UI布局"""
        from PyQt6.QtWidgets import QApplication
        font_family = QApplication.font().family()

        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)

        # 回复显示区域
        self.reply_label = QLabel(self)
        self.reply_label.setWordWrap(True)
        self.reply_label.setFont(QFont(font_family, 11))
        self.reply_label.setStyleSheet(f"color: {self.text_color.name()}; background: transparent;")
        self.reply_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.reply_label.setMinimumHeight(40)
        layout.addWidget(self.reply_label)

        # 思考指示器
        self.thinking_label = QLabel("... 思考中", self)
        self.thinking_label.setFont(QFont(font_family, 10))
        self.thinking_label.setStyleSheet(f"color: {self.accent_color.name()}; background: transparent;")
        self.thinking_label.hide()
        layout.addWidget(self.thinking_label)

        # 输入区域容器
        input_container = QWidget(self)
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(5)

        # 输入框
        self.input_edit = QTextEdit(self)
        self.input_edit.setMaximumHeight(60)
        self.input_edit.setPlaceholderText("和小U说点什么...")
        self.input_edit.setStyleSheet("""
            QTextEdit {
                border: 2px solid #e0c8e0;
                border-radius: 12px;
                padding: 6px;
                background: white;
                font-size: 11px;
                color: #3c3246;
            }
            QTextEdit:focus {
                border-color: #ffb6c1;
            }
        """)
        input_layout.addWidget(self.input_edit)

        # 发送按钮
        self.send_btn = QPushButton("发送", self)
        self.send_btn.setFixedSize(50, 36)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffb6c1, stop:1 #ff91a4);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ff91a4, stop:1 #ff7a94);
            }
            QPushButton:pressed {
                background: #ff7a94;
            }
        """)
        self.send_btn.clicked.connect(self._on_send)
        input_layout.addWidget(self.send_btn)

        layout.addWidget(input_container)

        # 连接回车键发送
        self.input_edit.keyPressEvent = self._input_key_press

        # 阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def _input_key_press(self, event):
        """处理输入框按键事件"""
        if (event.key() == Qt.Key.Key_Return or 
            event.key() == Qt.Key.Key_Enter):
            modifiers = int(event.modifiers())
            if modifiers & int(Qt.KeyboardModifier.ShiftModifier):
                # Shift+Enter 换行
                QTextEdit.keyPressEvent(self.input_edit, event)
            else:
                # Enter 发送
                self._on_send()
        else:
            QTextEdit.keyPressEvent(self.input_edit, event)

    def _on_send(self):
        """发送消息"""
        text = self.input_edit.toPlainText().strip()
        if text:
            self.message_sent.emit(text)
            self.input_edit.clear()

    def show_thinking(self):
        """显示思考状态"""
        self.is_thinking = True
        self.thinking_label.show()
        self.reply_label.setText("")
        self.thinking_started.emit()

    def show_reply(self, text: str, animate: bool = True):
        """
        显示回复文本
        
        Args:
            text: 回复文本
            animate: 是否打字机动画效果
        """
        self.is_thinking = False
        self.thinking_label.hide()
        self.current_text = text

        if animate and len(text) > 10:
            # 打字机效果
            self.typing_index = 0
            if self.typing_timer is None:
                self.typing_timer = QTimer(self)
                self.typing_timer.timeout.connect(self._typing_tick)
            self.typing_timer.start(40)  # 每40ms一个字
        else:
            self.reply_label.setText(text)

    def _typing_tick(self):
        """打字机动画 tick"""
        if self.typing_index < len(self.current_text):
            self.typing_index += 1
            self.reply_label.setText(self.current_text[:self.typing_index])
        else:
            self.typing_timer.stop()

    def show_bubble(self, pos_x: int, pos_y: int):
        """在指定位置显示气泡（带动画）"""
        self.move(pos_x, pos_y)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.start()

    def hide_bubble(self):
        """隐藏气泡（带淡出动画）"""
        self._fade_animation.finished.connect(self.hide)
        self._fade_animation.setStartValue(1.0)
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.start()

    def cancel_hide_animation(self):
        """取消正在进行的隐藏动画"""
        try:
            self._fade_animation.finished.disconnect(self.hide)
        except TypeError:
            pass

    def paintEvent(self, event):
        """绘制圆角气泡背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制圆角矩形
        path = QPainterPath()
        rect = QRectF(0, 0, self.width(), self.height())
        path.addRoundedRect(rect, 18, 18)

        # 填充背景
        painter.fillPath(path, QBrush(self.bg_color))

        # 绘制边框
        pen = QPen(self.border_color, 2)
        painter.setPen(painter.drawPath(path))

        # 绘制顶部装饰条
        accent_path = QPainterPath()
        accent_path.addRoundedRect(QRectF(0, 0, self.width(), 4), 18, 18)
        painter.fillPath(accent_path, QBrush(self.accent_color))

    def show_preset_message(self, text: str, duration: int = 4000):
        """
        显示预设消息（短暂提示，无输入框）
        
        Args:
            text: 提示文字
            duration: 显示时长(ms)
        """
        # 切换到预设模式：隐藏输入区，只显示文字
        self.input_edit.hide()
        self.send_btn.hide()
        self.show_reply(text, animate=True)

        # 自动关闭定时器
        QTimer.singleShot(duration, self._auto_close)

    def _auto_close(self):
        """自动关闭气泡"""
        self.close_requested.emit()

    def reset_to_chat_mode(self):
        """重置为聊天模式（显示输入框）"""
        self.input_edit.show()
        self.send_btn.show()
        self.reply_label.setText("")
        self.thinking_label.hide()

    def closeEvent(self, event):
        """关闭事件清理"""
        if self.typing_timer is not None:
            self.typing_timer.stop()
        super().closeEvent(event)


class SimpleMessagePopup(QWidget):
    """简单的消息弹窗（用于预设语句）"""

    def __init__(self, text: str, parent=None, duration: int = 3500):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.text = text
        self.duration = duration
        self.opacity = 1.0

        # 计算大小
        from PyQt6.QtWidgets import QApplication
        font = QFont(QApplication.font().family(), 11)
        fm = QFontMetrics(font)
        text_width = fm.horizontalAdvance(text) + 40
        text_height = fm.height() + 20
        
        self.setFixedSize(min(text_width, 280), max(text_height, 38))

        # 关闭定时器
        QTimer.singleShot(duration, self._start_fade_out)

        # 淡出计时器
        self._fade_timer = QTimer(self)
        self._fade_timer.timeout.connect(self._fade_step)

    def _start_fade_out(self):
        """开始淡出"""
        self._fade_timer.start(30)

    def _fade_step(self):
        """淡出步进"""
        self.opacity -= 0.05
        self.setWindowOpacity(max(0.0, self.opacity))
        if self.opacity <= 0:
            self._fade_timer.stop()
            self.close()

    def paintEvent(self, event):
        """绘制"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        path.addRoundedRect(rect, 16, 16)

        # 背景
        bg_color = QColor(45, 35, 52, 235)
        painter.fillPath(path, QBrush(bg_color))

        # 文字
        painter.setPen(QColor(255, 255, 255, 245))
        font = painter.font()
        font.setPointSize(11)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text)
