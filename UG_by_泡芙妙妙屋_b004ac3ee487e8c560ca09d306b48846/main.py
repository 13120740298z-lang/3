"""
小U - Windows 桌面宠物
基于 Live2D Cubism SDK + OpenGL 渲染
"""

import os
import sys
import time
import random
import logging
import ctypes
import platform
from pathlib import Path

import pygame
import tkinter as tk
from datetime import datetime

# 项目模块
from config import (
    API_KEY, API_ENDPOINT, MODEL_NAME, MAX_TOKENS, TEMPERATURE,
    SYSTEM_PROMPT, PRESET_MESSAGES, WINDOW_WIDTH, WINDOW_HEIGHT, INITIAL_AFFECTION
)
from live2d_engine import Live2DRenderer, ExpressionManager

import platform as platform_module

# 检查 OpenGL
try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
    OPENGL_AVAILABLE = True
except ImportError as e:
    logging.warning(f"PyOpenGL 未安装: {e}")
    OPENGL_AVAILABLE = False

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


# ==================== Windows 透明窗口设置 ====================
try:
    user32 = ctypes.windll.user32
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW = 0x00020000

    def set_window_transparent(hwnd, transparent=True):
        """设置窗口透明/可穿透"""
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if transparent:
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
        else:
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style & ~WS_EX_TRANSPARENT | WS_EX_LAYERED)

    def set_window_opaque(hwnd):
        """设置窗口不透明但仍透明背景"""
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED & ~WS_EX_TRANSPARENT)

except Exception as e:
    logger.warning(f"Windows API 调用失败: {e}")
    def set_window_transparent(hwnd, transparent=True): pass
    def set_window_opaque(hwnd): pass


# ==================== 对话气泡 (Tkinter) ====================
class ChatBubble:
    """对话气泡 UI - Tkinter 弹出窗口"""

    def __init__(self, on_send, on_close):
        self.on_send = on_send
        self.on_close = on_close
        self.root = None
        self.input_entry = None
        self.send_btn = None
        self.response_label = None
        self.is_thinking = False
        self.response_timer = None

    def show(self):
        """显示对话窗口"""
        if self.root is not None:
            self.root.destroy()

        # 创建窗口
        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.configure(bg='#2d2d2d')

        # 获取屏幕尺寸，居中显示
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()

        # 窗口大小和位置
        w, h = 320, 240
        x = sw // 2 - w // 2
        y = sh - h - 120
        self.root.geometry(f'{w}x{h}+{x}+{y}')

        # 主框架
        main_frame = tk.Frame(self.root, bg='#2d2d2d', padx=12, pady=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题栏
        title = tk.Label(main_frame, text='和小U聊天', fg='#ffb6c1', bg='#2d2d2d',
                         font=('Microsoft YaHei', 11, 'bold'))
        title.pack(anchor='w')

        # 关闭按钮
        close_btn = tk.Button(main_frame, text='×', command=self.hide,
                              bg='#2d2d2d', fg='#888', font=('Arial', 14, 'bold'),
                              relief=tk.FLAT, padx=4, pady=0,
                              cursor='hand2', bd=0)
        close_btn.pack(anchor='e')

        # 回复显示区
        self.response_label = tk.Label(main_frame, text='双击和我说话吧～ (｡･ω･｡)',
                                       fg='#ddd', bg='#1e1e1e', font=('Microsoft YaHei', 9),
                                       wraplength=280, justify='left', anchor='nw',
                                       padx=10, pady=8)
        self.response_label.pack(fill=tk.X, pady=(8, 8))

        # 输入框
        self.input_entry = tk.Entry(main_frame, bg='#1e1e1e', fg='#fff',
                                     font=('Microsoft YaHei', 10), insertbackground='#fff',
                                     relief=tk.FLAT, bd=0)
        self.input_entry.pack(fill=tk.X, ipady=8, pady=(0, 8))
        self.input_entry.bind('<Return>', lambda e: self._send())
        self.input_entry.focus_set()

        # 发送按钮
        self.send_btn = tk.Button(main_frame, text='发送', command=self._send,
                                   bg='#ffb6c1', fg='#333', font=('Microsoft YaHei', 9, 'bold'),
                                   relief=tk.FLAT, cursor='hand2', padx=16, pady=4)
        self.send_btn.pack()

    def _send(self):
        """发送消息"""
        text = self.input_entry.get().strip()
        if not text or self.is_thinking:
            return
        self.input_entry.delete(0, tk.END)
        self.show_thinking()
        self.on_send(text)

    def show_thinking(self):
        """显示思考状态"""
        self.is_thinking = True
        self.response_label.config(text='小U 在思考... (´･ω･`)')
        self.send_btn.config(state=tk.DISABLED)

    def show_response(self, text: str):
        """显示回复"""
        self.is_thinking = False
        self.send_btn.config(state=tk.NORMAL)
        self.response_label.config(text=f'小U: {text}')

        # 5秒后自动关闭
        if self.response_timer:
            self.root.after_cancel(self.response_timer)
        self.response_timer = self.root.after(5000, self.hide)

    def hide(self):
        """隐藏窗口"""
        if self.root:
            self.root.withdraw()
        self.on_close()

    def destroy(self):
        """销毁窗口"""
        if self.root:
            self.root.destroy()
            self.root = None


# ==================== 简单消息弹窗 ====================
class SimplePopup:
    """简单气泡消息弹窗"""

    def __init__(self, text: str, duration: float = 3.0):
        self.root = None
        self.text = text
        self.duration = duration
        self._show()

    def _show(self):
        sw = self.root.winfo_screenwidth() if self.root else 1920
        sh = self.root.winfo_screenheight() if self.root else 1080

        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.configure(bg='#1e1e1e')

        w, h = 280, 80
        x = sw - w - 30
        y = sh - h - 100
        self.root.geometry(f'{w}x{h}+{x}+{y}')

        frame = tk.Frame(self.root, bg='#1e1e1e', padx=12, pady=8)
        frame.pack(fill=tk.BOTH, expand=True)

        label = tk.Label(frame, text=self.text, fg='#fff', bg='#1e1e1e',
                         font=('Microsoft YaHei', 10), wraplength=250,
                         justify='center')
        label.pack(expand=True)

        # 动画淡入
        self.root.attributes('-alpha', 0.0)
        for i in range(11):
            self.root.attributes('-alpha', i / 10.0)
            self.root.update()
            time.sleep(0.02)

        # 自动关闭
        self.root.after(int(self.duration * 1000), self._fade_out)

    def _fade_out(self):
        """淡出消失"""
        for i in range(10, -1, -1):
            if self.root:
                self.root.attributes('-alpha', i / 10.0)
                self.root.update()
                time.sleep(0.03)
        self._close()

    def _close(self):
        if self.root:
            self.root.destroy()
            self.root = None


# ==================== 主程序 ====================
class DesktopPet:
    """桌面宠物主程序"""

    def __init__(self):
        # 初始化 Pygame
        os.environ['SDL_VIDEO_WINDOW_POS'] = '0,0'
        pygame.init()

        # 窗口尺寸
        self.width, self.height = WINDOW_WIDTH, WINDOW_HEIGHT
        
        # 选择渲染模式
        self.use_opengl = OPENGL_AVAILABLE
        
        if self.use_opengl:
            # OpenGL 模式
            pygame.display.set_mode(
                (self.width, self.height),
                pygame.NOFRAME | pygame.DOUBLEBUF | pygame.OPENGL
            )
            self._init_opengl()
            logger.info("使用 OpenGL 渲染模式")
        else:
            # 普通模式（fallback）
            pygame.display.set_mode(
                (self.width, self.height),
                pygame.NOFRAME | pygame.SRCALPHA
            )
            logger.warning("OpenGL 不可用，使用普通渲染模式")

        pygame.display.set_caption('小U - 桌面宠物')
        pygame.display.set_icon(pygame.Surface((1, 1)))

        # 设置窗口属性
        self._setup_window()

        # 加载资源路径
        script_dir = Path(__file__).parent.resolve()
        model_dir = str(script_dir / 'models' / 'UG')

        # 初始化 Live2D 渲染器
        self.renderer = Live2DRenderer(model_dir, init_opengl=self.use_opengl)
        
        if self.use_opengl:
            # OpenGL 已初始化，现在完成 Live2D 渲染器初始化
            try:
                self.renderer.renderer.finalize_init()
                logger.info("Live2D 渲染器初始化完成")
            except Exception as e:
                logger.error(f"Live2D 渲染器初始化失败: {e}")
        
        self.expression_manager = ExpressionManager(model_dir)
        
        # 尝试导入可选模块
        try:
            from llm_client import LLMClient
            from memory_manager import MemoryManager
            from token_monitor import TokenMonitor
            self.llm_client = LLMClient()
            self.memory_manager = MemoryManager()
            self.token_monitor = TokenMonitor()
            self.has_llm = True
        except ImportError as e:
            logger.warning(f"可选模块未安装: {e}")
            self.llm_client = None
            self.memory_manager = None
            self.token_monitor = None
            self.has_llm = False

        # 对话系统
        self.chat_bubble = None
        self.is_in_chat_mode = False
        self.popups: list[SimplePopup] = []

        # 行为状态
        self.pet_state = "idle"
        self.idle_action_timer = random.uniform(10.0, 30.0)
        self.micro_action_timer = random.uniform(3.0, 10.0)
        self.active_expression = "default"
        self.expression_reset_timer = 0.0

        # 点击统计（用于连击检测）
        self.click_count = 0
        self.click_timer = 0.0

        # 鼠标状态
        self.mouse_x = 0.5
        self.mouse_y = 0.5

        # 拖拽状态
        self.is_dragging = False
        self.drag_offset = (0, 0)
        self.window_x = 0
        self.window_y = 0

        # 透明度动画
        self.alpha = 0.0
        self.alpha_target = 1.0

        # 时钟
        self.clock = pygame.time.Clock()
        self.running = True

        # 好感度相关
        self.affection = 30
        if self.memory_manager:
            self.affection = self.memory_manager.affection

        # 问候标记
        self.greeted_today = False

        # 创建托盘图标
        try:
            self.tray_icon = TkTrayManager(self)
        except Exception as e:
            logger.warning(f"托盘图标创建失败: {e}")
            self.tray_icon = None

        # 每日问候
        self._daily_greeting()

        logger.info("小U 初始化完成！")

    def _init_opengl(self):
        """初始化 OpenGL"""
        try:
            # 设置视口
            glViewport(0, 0, self.width, self.height)
            
            # 设置投影矩阵
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            
            # 正交投影（2D）
            glOrtho(0, self.width, self.height, 0, -1, 1)
            
            # 模型视图矩阵
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            
            # 启用透明
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            
            # 禁用深度测试
            glDisable(GL_DEPTH_TEST)
            
            # 清空颜色（透明）
            glClearColor(0.0, 0.0, 0.0, 0.0)
            
            logger.info("OpenGL 初始化完成")
            
        except Exception as e:
            logger.error(f"OpenGL 初始化失败: {e}")
            self.use_opengl = False

    def _setup_window(self):
        """设置窗口属性（透明、置顶等）"""
        if platform_module.system() != 'Windows':
            return

        try:
            hwnd = pygame.display.get_wm_info()['window']
            # 设置透明背景
            if not self.use_opengl:
                self.screen.fill((0, 0, 0, 0))

            # 设置分层窗口
            set_window_transparent(hwnd, True)

            # 移动到右下角
            user32 = ctypes.windll.user32
            sw = user32.GetSystemMetrics(0)
            sh = user32.GetSystemMetrics(1)
            taskbar_h = user32.GetSystemMetrics(5)
            self.window_x = sw - self.width - 20
            self.window_y = sh - self.height - taskbar_h - 10

            # 设置窗口位置
            SWP_SHOWWINDOW = 0x0040
            user32.SetWindowPos(hwnd, 0, self.window_x, self.window_y,
                               self.width, self.height, SWP_SHOWWINDOW)

            logger.info(f"窗口位置设置: ({self.window_x}, {self.window_y})")
        except Exception as e:
            logger.error(f"窗口设置失败: {e}")

    def _daily_greeting(self):
        """每日问候"""
        if not self.greeted_today:
            greetings = [
                "主人早呀！今天也要加油哦～ ٩(๑❛ᴗ❛๑)۶",
                "小U 来啦！有什么需要帮忙的吗？",
                "啊，主人来啦！我等你好久了呢～",
                "新的一天开始啦！小U 随时待命！",
                "嗨嗨～ 看到主人好开心！(≧▽≦)/",
            ]
            self.show_popup(random.choice(greetings), 4.0)
            self.greeted_today = True

    def show_popup(self, text: str, duration: float = 3.0):
        """显示简单消息弹窗"""
        try:
            popup = SimplePopup(text, duration)
            self.popups.append(popup)
        except Exception as e:
            logger.warning(f"弹窗显示失败: {e}")

    def set_expression(self, name: str, duration: float = 3.0):
        """设置表情"""
        self.active_expression = name
        self.expression_reset_timer = duration
        self.renderer.set_expression(name, duration)

    def handle_click(self, pos: tuple[int, int]):
        """处理点击"""
        # 检测是否点击在宠物上
        model_rect = self.renderer.get_rect_with_hover()
        if model_rect is None:
            return

        # 相对位置
        rel_x = pos[0] - model_rect[0]
        rel_y = pos[1] - model_rect[1]

        if (0 <= rel_x < model_rect[2] and 0 <= rel_y < model_rect[3]):
            # 点击在宠物上
            self._on_pet_clicked()
        else:
            # 点击在宠物外但窗口内 - 关闭对话
            if self.chat_bubble and self.chat_bubble.root:
                try:
                    self.chat_bubble.root.withdraw()
                except:
                    pass
            self.is_in_chat_mode = False

    def _on_pet_clicked(self):
        """宠物被点击"""
        self.click_count += 1
        self.click_timer = 1.0

        if self.click_count >= 5:
            # 连击5次 - 生气
            self.set_expression("8punch", 3.0)
            self.show_popup("别戳啦！好疼的！(╯°□°)╯", 3.0)
            if self.memory_manager:
                self.memory_manager._change_affection(-2, "angry_poke")
                self.affection = self.memory_manager.affection
            self.click_count = 0
            return

        # 单击 - 随机表情
        expr = self.expression_manager.get_random_expression()
        self.set_expression(expr, 3.0)
        
        # 触发动作
        self.renderer.renderer.start_motion("Idle", -1, priority=2)
        
        if self.memory_manager:
            self.memory_manager._change_affection(1, "click")
            self.affection = self.memory_manager.affection

        # 偶尔说句话
        if random.random() < 0.3:
            words = ["喵～", "嘿嘿～", "主人想我了吗？", "呀！", "好痒～"]
            self.show_popup(random.choice(words), 2.0)

    def handle_double_click(self, pos: tuple[int, int]):
        """处理双击 - 打开对话"""
        model_rect = self.renderer.get_rect_with_hover()
        if model_rect is None:
            return

        rel_x = pos[0] - model_rect[0]
        rel_y = pos[1] - model_rect[1]

        if 0 <= rel_x < model_rect[2] and 0 <= rel_y < model_rect[3]:
            self._open_chat()
        else:
            # 双击外部，关闭对话
            if self.chat_bubble and self.chat_bubble.root:
                try:
                    self.chat_bubble.root.withdraw()
                except:
                    pass
            self.is_in_chat_mode = False

    def _open_chat(self):
        """打开对话窗口"""
        self.is_in_chat_mode = True
        if self.chat_bubble is None:
            self.chat_bubble = ChatBubble(
                on_send=self._on_chat_message,
                on_close=self._on_chat_closed
            )
        self.chat_bubble.show()

    def _on_chat_closed(self):
        """对话关闭"""
        self.is_in_chat_mode = False

    def _on_chat_message(self, text: str):
        """发送聊天消息"""
        logger.info(f"发送消息: {text}")

        if not self.has_llm:
            self.chat_bubble.show_response("小U 正在学习中，暂时无法回复...")
            return

        # 记录到记忆
        self.memory_manager.add_chat_to_memory(text, "")

        # Token 监控
        estimated = len(text) // 2 + 50
        if self.token_monitor.is_budget_exceeded():
            resp = random.choice(PRESET_MESSAGES['greeting'])
            self.chat_bubble.show_response(resp)
            return

        self.token_monitor.add_usage(estimated, estimated)

        # 调用 LLM
        try:
            context = self.memory_manager.get_context_for_llm()
            response = self.llm_client.chat(
                text,
                context=context,
                system_prompt=self._get_system_prompt()
            )
            self.memory_manager.add_chat_to_memory(text, response)

            resp_tokens = len(response) // 2
            self.token_monitor.add_usage(resp_tokens, resp_tokens)

            self.chat_bubble.show_response(response)
            self._react_to_emotion(response)

        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            self.chat_bubble.show_response("嗯...网络好像不太好呢 (´;ω;`)")

        # 好感度 +2
        self.memory_manager._change_affection(2, "chat")
        self.affection = self.memory_manager.affection

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        prompt = SYSTEM_PROMPT
        if self.affection >= 70:
            prompt += "\n当前好感度较高，语气可以更亲昵。"
        elif self.affection >= 40:
            prompt += "\n当前好感度一般，保持友好但不过分热情。"
        else:
            prompt += "\n当前好感度较低，需要更努力讨好主人。"
        return prompt

    def _react_to_emotion(self, text: str):
        """根据回复内容调整表情"""
        if self.llm_client:
            try:
                emotion = self.llm_client.detect_emotion(text)
                emotion_map = {
                    'positive': '3clever',
                    'surprise': '4OAO',
                    'negative': '5QAQ',
                    'angry': '6i gi a ri',
                    'excited': '2mic',
                }
                if emotion in emotion_map:
                    self.set_expression(emotion_map[emotion], 4.0)
            except:
                pass

    def update_behavior(self, dt: float):
        """更新自主行为"""
        # 连击计时
        if self.click_timer > 0:
            self.click_timer -= dt
            if self.click_timer <= 0:
                self.click_count = 0

        # 表情恢复
        if self.expression_reset_timer > 0:
            self.expression_reset_timer -= dt
            if self.expression_reset_timer <= 0:
                self.set_expression("default", 0)

        # 好感度衰减
        if self.memory_manager:
            self.memory_manager.check_ignore_penalty()
            self.affection = self.memory_manager.affection

        # 非对话模式下的自主行为
        if not self.is_in_chat_mode:
            # 微动作
            self.micro_action_timer -= dt
            if self.micro_action_timer <= 0:
                self.micro_action_timer = random.uniform(3.0, 10.0)
                if random.random() < 0.3:
                    # 随机表情
                    self.renderer.set_expression(
                        self.expression_manager.get_random_expression(), 
                        3.0
                    )

            # 随机动作
            self.idle_action_timer -= dt
            if self.idle_action_timer <= 0:
                self.idle_action_timer = random.uniform(10.0, 30.0)
                r = random.random()
                if r < 0.4:
                    self.renderer.renderer.start_motion("Idle", -1, priority=1)
                elif r < 0.6:
                    self.show_popup(random.choice(PRESET_MESSAGES['random']), 3.0)

    def handle_event(self, event: pygame.event.Event):
        """处理事件"""
        etype = event.type

        if etype == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.is_dragging = True
                rect = self.renderer.get_rect_with_hover()
                if rect and self._collide_point(rect, event.pos):
                    self.is_dragging = "click"
                else:
                    self.is_dragging = "move"

        elif etype == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if self.is_dragging == "click":
                    self.handle_click(event.pos)
                self.is_dragging = False

        elif etype == pygame.MOUSEMOTION:
            self.mouse_x = event.pos[0] / self.width
            self.mouse_y = event.pos[1] / self.height

            if self.is_dragging == "move":
                try:
                    hwnd = pygame.display.get_wm_info()['window']
                    user32 = ctypes.windll.user32
                    x, y = event.pos
                    user32.SetWindowPos(hwnd, 0, x - self.width//2, y - self.height//2, 0, 0, 0x0001)
                except:
                    pass
                    
            # 更新拖拽
            self.renderer.renderer.set_drag(
                (event.pos[0] - self.width // 2) / 100,
                (event.pos[1] - self.height // 2) / 100
            )

    def _collide_point(self, rect, pos):
        """检测点是否在矩形内"""
        return (rect[0] <= pos[0] <= rect[0] + rect[2] and
                rect[1] <= pos[1] <= rect[1] + rect[3])

    def run(self):
        """主循环"""
        running = True
        last_click_time = 0
        last_click_pos = (0, 0)

        while running:
            dt = self.clock.tick(60) / 1000.0

            # 事件处理
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        now = time.time()
                        if now - last_click_time < 0.3:
                            dx = event.pos[0] - last_click_pos[0]
                            dy = event.pos[1] - last_click_pos[1]
                            if abs(dx) < 20 and abs(dy) < 20:
                                self.handle_double_click(event.pos)
                                last_click_time = 0
                                continue
                        last_click_time = now
                        last_click_pos = event.pos

                        rect = self.renderer.get_rect_with_hover()
                        if rect and self._collide_point(rect, event.pos):
                            self.is_dragging = "click"
                        else:
                            self.is_dragging = "move"

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        if self.is_dragging == "click":
                            self.handle_click(event.pos)
                        elif self.is_dragging == "move":
                            try:
                                hwnd = pygame.display.get_wm_info()['window']
                                user32 = ctypes.windll.user32
                                x, y = event.pos
                                user32.SetWindowPos(hwnd, 0, x - self.width//2, y - self.height//2, 0, 0, 0x0001)
                            except:
                                pass
                        self.is_dragging = False

                elif event.type == pygame.MOUSEMOTION:
                    self.mouse_x = event.pos[0] / self.width
                    self.mouse_y = event.pos[1] / self.height

                    if self.is_dragging == "move":
                        try:
                            hwnd = pygame.display.get_wm_info()['window']
                            user32 = ctypes.windll.user32
                            x, y = event.pos
                            user32.SetWindowPos(hwnd, 0, x - self.width//2, y - self.height//2, 0, 0, 0x0001)
                        except:
                            pass

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.chat_bubble and self.chat_bubble.root:
                            try:
                                self.chat_bubble.root.withdraw()
                            except:
                                pass
                        self.is_in_chat_mode = False
                    elif event.key == pygame.K_SPACE:
                        expr = self.expression_manager.get_random_expression()
                        self.set_expression(expr, 3.0)
                    elif event.key == pygame.K_r:
                        self._toggle_window()

            # 更新
            self.renderer.update(dt, self.mouse_x, self.mouse_y)
            self.update_behavior(dt)

            # 淡入
            if self.alpha < self.alpha_target:
                self.alpha = min(self.alpha + dt * 2, self.alpha_target)

            # 渲染
            self._render()

            # 清理过期弹窗
            self.popups = [p for p in self.popups if p.root is not None]

        self._cleanup()

    def _render(self):
        """渲染帧"""
        if self.use_opengl:
            # OpenGL 渲染
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glLoadIdentity()
            
            # 设置正交投影
            glOrtho(0, self.width, self.height, 0, -1, 1)
            
            # 渲染 Live2D 模型
            self.renderer.render(None)
            
            pygame.display.flip()
        else:
            # 普通渲染（fallback）
            self.screen.fill((0, 0, 0, 0))
            pygame.display.flip()

    def _toggle_window(self):
        """切换窗口显示/隐藏"""
        try:
            hwnd = pygame.display.get_wm_info()['window']
            user32 = ctypes.windll.user32
            SWP_SHOWWINDOW = 0x0040
            SWP_HIDEWINDOW = 0x0080
            if self.alpha_target > 0:
                user32.ShowWindow(hwnd, SWP_HIDEWINDOW)
                self.alpha_target = 0
            else:
                user32.ShowWindow(hwnd, SWP_SHOWWINDOW)
                self.alpha_target = 1
        except Exception as e:
            logger.error(f"窗口切换失败: {e}")

    def _cleanup(self):
        """清理退出"""
        logger.info("小U 退出...")
        
        # 释放 Live2D
        if self.use_opengl:
            try:
                import live2d.v3 as live2d
                live2d.glRelease()
                live2d.dispose()
            except:
                pass
        
        # 释放渲染器
        try:
            self.renderer.renderer.dispose()
        except:
            pass
        
        if self.chat_bubble:
            self.chat_bubble.destroy()
            
        pygame.quit()
        sys.exit(0)


# ==================== Tkinter 托盘管理器 ====================
class TkTrayManager:
    """使用 Tkinter 的系统托盘管理"""

    def __init__(self, pet):
        self.pet = pet
        self.root = tk.Tk()
        self.root.withdraw()
        self._create_menu()
        self._poll()

    def _create_menu(self):
        """创建右键菜单"""
        menu = tk.Menu(self.root, tearoff=0, bg='#1e1e1e', fg='#fff',
                      font=('Microsoft YaHei', 9))
        menu.add_command(label='✨ 召唤小U', command=self._show_window)
        menu.add_command(label='🔕 安静模式', command=self._toggle_quiet)
        menu.add_separator()
        menu.add_command(label='💕 好感度查看', command=self._show_affection)
        menu.add_separator()
        menu.add_command(label='❌ 退出', command=self._exit)
        self.menu = menu

    def _show_menu(self, x, y):
        self.menu.post(x, y)

    def _show_window(self):
        try:
            hwnd = pygame.display.get_wm_info()['window']
            user32 = ctypes.windll.user32
            user32.ShowWindow(hwnd, 0x0040)
            self.pet.alpha_target = 1.0
        except:
            pass

    def _toggle_quiet(self):
        self.pet.show_popup("安静模式已开启～", 2.0)

    def _show_affection(self):
        aff = self.pet.affection
        level = "陌生" if aff < 20 else "熟悉" if aff < 50 else "喜欢" if aff < 80 else "挚友"
        self.pet.show_popup(f"💕 好感度: {aff}/100 ({level})", 3.0)

    def _exit(self):
        self.pet.running = False

    def _poll(self):
        self.root.after(500, self._poll)


# ==================== 入口 ====================
def main():
    """程序入口"""
    logger.info("=" * 40)
    logger.info("  [DesktopPet] Starting xiaoU...")
    logger.info("  使用 Live2D Cubism SDK 渲染")
    logger.info("=" * 40)

    try:
        pet = DesktopPet()
        pet.run()
    except KeyboardInterrupt:
        logger.info("收到退出信号，正在关闭...")
        pygame.quit()
    except Exception as e:
        logger.error(f"程序异常退出: {e}", exc_info=True)
        pygame.quit()
        raise


if __name__ == '__main__':
    main()
