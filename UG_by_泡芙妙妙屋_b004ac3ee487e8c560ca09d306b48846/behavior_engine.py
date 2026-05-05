"""
行为引擎
控制宠物的自主行为：待机动作、随机活动、环境感知、主动搭话等
"""

import random
import time
import logging
import threading
from enum import Enum
from typing import Callable, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal as Signal
from PyQt6.QtWidgets import QApplication

from config import PRESET_MESSAGES
from live2d_engine import ExpressionManager

logger = logging.getLogger(__name__)


class PetState(Enum):
    """宠物状态枚举"""
    IDLE = "idle"           # 待机
    ACTIVE = "active"       # 活动中
    SLEEPING = "sleeping"   # 睡觉
    CHATTING = "chatting"   # 对话中
    ANGRY = "angry"         # 生气


class BehaviorEngine(QObject):
    """
    自主行为引擎
    
    控制宠物在非对话状态下的所有自主行为
    """

    # 信号
    expression_requested = Signal(str, float)  # (表情名, 持续时间秒)
    message_requested = Signal(str)             # 显示消息
    state_changed = Signal(object)              # 状态变更
    position_move_requested = Signal(int, int)  # 移动位置

    def __init__(self, expression_manager: ExpressionManager):
        super().__init__()

        self.expression_manager = expression_manager
        self.state = PetState.IDLE

        # 时间追踪
        self.last_user_interaction = time.time()  # 最后一次用户交互
        self.start_time = time.time()              # 启动时间
        self.last_idle_action = time.time()        # 上次待机微动作
        self.last_random_action = time.time()      # 上次随机动作
        self.last_active_chat = time.time()        # 上次主动搭话

        # 配置
        self.eco_mode = False
        self.quiet_mode = False  # 安静模式（不主动搭话）

        # 定时器
        self._behavior_timer = QTimer(self)
        self._behavior_timer.timeout.connect(self._tick)
        self._behavior_timer.start(1000)  # 每秒检查一次

        # 鼠标位置追踪（用于检测用户是否在线）
        self._last_mouse_pos = None
        self._no_activity_start = None

        logger.info("行为引擎启动")

    def record_interaction(self):
        """记录用户交互"""
        self.last_user_interaction = time.time()
        self._no_activity_start = None

        # 如果在睡觉状态，唤醒
        if self.state == PetState.SLEEPING:
            self._wake_up()

    def set_eco_mode(self, enabled: bool):
        """设置省电模式"""
        self.eco_mode = enabled
        logger.info(f"省电模式: {'开启' if enabled else '关闭'}")

    def set_quiet_mode(self, enabled: bool):
        """设置安静模式"""
        self.quiet_mode = enabled
        logger.info(f"安静模式: {'开启' if enabled else '关闭'}")

    def _get_current_hour(self) -> int:
        """获取当前小时"""
        import datetime
        return datetime.datetime.now().hour

    def _is_night_time(self) -> bool:
        """判断是否是夜晚时段 (23:00-06:00)"""
        hour = self._get_current_hour()
        return hour >= 23 or hour < 6

    def _seconds_since_last_interaction(self) -> float:
        """距离上次交互的秒数"""
        return time.time() - self.last_user_interaction

    def _tick(self):
        """每秒执行的行为检查"""
        now = time.time()

        # 检查是否需要进入睡觉状态
        inactive_seconds = self._seconds_since_last_interaction()
        if inactive_seconds > 1800 and self.state != PetState.SLEEPING:  # 30分钟
            self._enter_sleep()
            return

        if self.state == PetState.SLEEPING:
            return

        # 夜晚模式降低频率
        night_multiplier = 0.3 if self._is_night_time() else 1.0

        # 待机微动作检查 (10-30秒)
        idle_interval = random.uniform(10, 30) / (0.5 if self.eco_mode else 1.0)
        if now - self.last_idle_action > idle_interval:
            self._do_idle_action()
            self.last_idle_action = now

        # 随机动作检查 (3-8分钟)
        random_interval = random.uniform(180, 480) / night_multiplier
        if now - self.last_random_action > random_interval:
            self._do_random_action()
            self.last_random_action = now

        # 主动搭话检查 (20-40分钟)，安静模式下跳过
        if not self.quiet_mode:
            chat_interval = random.uniform(1200, 2400) / night_multiplier
            if now - self.last_active_chat > chat_interval:
                self._do_active_chat()
                self.last_active_chat = now

    def _do_idle_action(self):
        """执行待机微动作"""
        actions = [
            ("_blink_vary", 0),
            ("_head_tilt", 0),
            ("_stretch_mini", 0),
        ]
        action_name = random.choice(actions)[0]
        handler = getattr(self, action_name, None)
        if handler:
            handler()

    def _do_random_action(self):
        """执行随机大动作"""
        actions = [
            ("_action_desk",),
            ("_action_keyboard",),
            ("_action_mic",),
            ("_action_walk",),
            ("_action_sign",),
        ]
        action_name = random.choice(actions)[0]
        handler = getattr(self, action_name, None)
        if handler:
            handler()

    def _do_active_chat(self):
        """执行主动搭话"""
        categories = list(PRESET_MESSAGES.keys())
        # 根据时间段排除不适用的分类
        current_hour = self._get_current_hour()
        available_categories = [c for c in categories]

        if not (9 <= current_hour < 12):
            available_categories = [c for c in available_categories if c != "greeting_morning"]
        if not (17 <= current_hour < 22 or 6 <= current_hour < 9):
            available_categories = [c for c in available_categories if c != "greeting_night"]

        category = random.choice(available_categories)
        messages = PRESET_MESSAGES.get(category, [""])
        message = random.choice(messages)
        self.message_requested.emit(message)

    # ==================== 微动作 ====================

    def _blink_vary(self):
        """眨眼频率变化（通过表情管理器控制）"""
        pass  # 眨眼由 Live2D 引擎自动处理

    def _head_tilt(self):
        """轻轻歪头"""
        # 歪头效果通过参数调整实现
        self.expression_requested.emit("", 0)  # 触发一次参数刷新
        logger.debug("歪头微动作")

    def _stretch_mini(self):
        """伸懒腰（轻微）"""
        self.expression_requested.emit("stretch", 1.5)
        logger.debug("伸懒腰微动作")

    # ==================== 随机动作 ====================

    def _action_desk(self):
        """假装在书桌前忙"""
        self.expression_requested.emit("desk", 10)
        logger.info("随机动作: 书桌前")

    def _action_keyboard(self):
        """敲键盘"""
        self.expression_requested.emit("keyboard", 8)
        logger.info("随机动作: 敲键盘")

    def _action_mic(self):
        """哼歌/拿麦克风"""
        self.expression_requested.emit("mic", 5)
        msg = random.choice(["♪~ la la la~ ♪", "哼哼~今天天气真好呢"])
        self.message_requested.emit(msg)
        logger.info("随机动作: 拿麦克风唱歌")

    def _action_walk(self):
        """在屏幕上走动"""
        logger.info("随机动作: 屏幕上移动")
        # 发送移动信号给主窗口处理
        screen = QApplication.primaryScreen()
        if screen:
            screen_rect = screen.availableGeometry()
            start_x = 100
            end_x = screen_rect.width() - 500
            self.position_move_requested.emit(start_x, end_x)

    def _action_sign(self):
        """掏出小牌子吐槽"""
        roast_messages = PRESET_MESSAGES.get("roast", [""])
        msg = random.choice(roast_messages)
        self.message_requested.emit(msg)
        logger.info(f"随机动作: 吐槽牌子 - {msg}")

    # ==================== 状态切换 ====================

    def _enter_sleep(self):
        """进入睡觉状态"""
        if self.state != PetState.SLEEPING:
            self.state = PetState.SLEEPING
            self.expression_requested.emit("sleep", 0)  # 永久表情
            self.state_changed.emit(PetState.SLEEPING)
            logger.info("进入睡觉状态")
            
            # 如果是深夜，可能发一句晚安
            if self._is_night_time():
                night_msgs = PRESET_MESSAGES.get("greeting_night", [""])
                self.message_requested.emit(random.choice(night_msgs))

    def _wake_up(self):
        """从睡觉状态唤醒"""
        self.state = PetState.IDLE
        self.expression_requested.emit("", 0)  # 清除表情
        self.state_changed.emit(PetState.IDLE)

        # 说欢迎回来
        return_msgs = PRESET_MESSAGES.get("return_from_afk", [""])
        self.message_requested.emit(random.choice(return_msgs))
        logger.info("从睡觉状态唤醒")
