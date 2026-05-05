"""
系统托盘图标
提供右键菜单和双击快捷操作
"""

import logging
import logging
from typing import Optional, Callable

from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtWidgets import (
    QSystemTrayIcon, QMenu, QApplication,
    QMessageBox
)
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont, QBrush


class TrayIcon(QSystemTrayIcon):
    """系统托盘图标"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent

        # 创建自定义图标
        self.setIcon(self._create_tray_icon())
        self.setToolTip("小U - 桌面宠物")

        # 菜单回调（由主窗口设置）
        self._on_toggle_visibility: Optional[Callable] = None
        self._on_toggle_eco: Optional[Callable] = None
        self._on_toggle_quiet: Optional[Callable] = None
        self._on_show_affection: Optional[Callable] = None
        self._on_exit: Optional[Callable] = None

        # 状态标记
        self.pet_visible = True
        self.eco_mode = False
        self.quiet_mode = False

        # 构建菜单
        self._build_menu()

        # 信号连接
        self.activated.connect(self.on_activated)

        # 显示托盘图标
        self.show()
        logging.getLogger(__name__).info("系统托盘初始化完成")

    def _create_tray_icon(self) -> QIcon:
        """创建自定义托盘图标（粉色U字）"""
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(painter.RenderHint.Antialiasing)

        # 圆形背景
        painter.setBrush(QBrush(QColor(255, 182, 193)))
        painter.setPen(QColor(255, 150, 170))
        painter.drawEllipse(2, 2, 60, 60)

        # 绘制 "U" 字
        painter.setPen(QColor(255, 255, 255))
        font = QFont(["Segoe UI", "Microsoft YaHei", "sans-serif"], 32, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "U")

        painter.end()

        return QIcon(pixmap)

    def _build_menu(self):
        """构建右键菜单"""
        menu = QMenu()

        self.toggle_action = QAction("🙈 隐藏宠物", self)
        self.toggle_action.triggered.connect(self._on_toggle_clicked)
        menu.addAction(self.toggle_action)

        menu.addSeparator()

        self.eco_action = QAction("⚡ 省电模式 (30fps)", self)
        self.eco_action.setCheckable(True)
        self.eco_action.triggered.connect(self._on_eco_toggled)
        menu.addAction(self.eco_action)

        self.quiet_action = QAction("🤫 安静模式", self)
        self.quiet_action.setCheckable(True)
        self.quiet_action.triggered.connect(self._on_quiet_toggled)
        menu.addAction(self.quiet_action)

        menu.addSeparator()

        affection_action = QAction("❤️ 查看好感度", self)
        affection_action.triggered.connect(self._on_show_affection_clicked)
        menu.addAction(affection_action)

        token_action = QAction("📊 Token 用量", self)
        token_action.triggered.connect(self._on_show_token_clicked)
        menu.addAction(token_action)

        menu.addSeparator()

        about_action = QAction("ℹ️ 关于小U", self)
        about_action.triggered.connect(self._show_about)
        menu.addAction(about_action)

        exit_action = QAction("🚪 退出", self)
        exit_action.triggered.connect(self._on_exit_clicked)
        menu.addAction(exit_action)

        self.setContextMenu(menu)

    def on_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """处理托盘图标激活事件"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._on_toggle_clicked()

    def _on_toggle_clicked(self):
        """切换显示/隐藏"""
        if self._on_toggle_visibility:
            self._on_toggle_visibility()
            self.pet_visible = not self.pet_visible
            self.toggle_action.setText(
                "🙈 隐藏宠物" if self.pet_visible else "🐱 召唤宠物"
            )

    def _on_eco_toggled(self):
        """切换省电模式"""
        if self._on_toggle_eco:
            self._on_toggle_eco(self.eco_action.isChecked())
            self.eco_mode = self.eco_action.isChecked()

    def _on_quiet_toggled(self):
        """切换安静模式"""
        if self._on_toggle_quiet:
            self._on_toggle_quiet(self.quiet_action.isChecked())
            self.quiet_mode = self.quiet_action.isChecked()

    def _on_show_affection_clicked(self):
        """查看好感度"""
        if self._on_show_affection:
            self._on_show_affection()

    def _on_show_token_clicked(self):
        """查看Token用量"""
        if hasattr(self.parent_widget, '_show_token_status'):
            self.parent_widget._show_token_status()

    def _on_exit_clicked(self):
        """退出程序"""
        reply = QMessageBox.question(
            None, "确认退出",
            "确定要退出小U吗？\n(小U会想念你的...)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self._on_exit:
                self._on_exit()
            QApplication.quit()

    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            None,
            "关于小U",
            "<h3>🌸 小U - 桌面宠物 🌸</h3>"
            "<p>版本: 1.0.0</p>"
            "<p>一个可爱的 Live2D 桌面宠物</p>"
            "<p>模型: UG Official by 泡芙妙妙屋</p>"
            "<hr>"
            "<p>Powered by Live2D + PyQt6</p>"
            "<p>LLM: 小米 Mimo</p>"
        )

    # ==================== 回调设置 ====================

    def set_callbacks(
        self,
        on_toggle: Callable = None,
        on_eco: Callable[[bool], None] = None,
        on_quiet: Callable[[bool], None] = None,
        on_affection: Callable = None,
        on_exit: Callable = None
    ):
        """设置菜单回调函数"""
        if on_toggle:
            self._on_toggle_visibility = on_toggle
        if on_eco:
            self._on_toggle_eco = on_eco
        if on_quiet:
            self._on_toggle_quiet = on_quiet
        if on_affection:
            self._on_show_affection = on_affection
        if on_exit:
            self._on_exit = on_exit

    def show_notification(self, title: str, message: str, duration: int = 3000):
        """显示系统通知"""
        self.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, duration)
