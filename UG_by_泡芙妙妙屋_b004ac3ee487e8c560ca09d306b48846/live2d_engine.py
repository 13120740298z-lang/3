"""
Live2D 渲染引擎 v3 - 使用 Cubism SDK
正确加载 .moc3 模型文件，实现完整的动画效果
"""

import os
import sys
import logging
import random
import math
from pathlib import Path
from typing import Optional

# 尝试导入 live2d-py
try:
    import live2d.v3 as live2d
    from live2d.v3 import Model, LAppModel
    LIV2D_AVAILABLE = True
except ImportError as e:
    logging.warning(f"live2d-py 未安装: {e}")
    LIV2D_AVAILABLE = False
    Model = None
    LAppModel = None

logger = logging.getLogger(__name__)


class CubismLive2DRenderer:
    """使用 Cubism SDK 的 Live2D 渲染器"""

    def __init__(self, model_dir: str, init_opengl: bool = False):
        self.model_dir = Path(model_dir)
        self.model: Optional[Model] = None
        self.model_loaded = False
        self.renderer_ready = False
        self.needs_opengl_init = not init_opengl
        
        # 窗口尺寸
        self.view_width = 400
        self.view_height = 500
        
        # 模型显示参数
        self.scale = 0.08
        self.offset_x = 0.0
        self.offset_y = 0.0
        
        # 动画状态
        self.breath_phase = 0.0
        self.hover_phase = 0.0
        self.hover_offset = 0.0
        
        # 鼠标跟随
        self.mouse_x = 0.5
        self.mouse_y = 0.5
        self.drag_x = 0.0
        self.drag_y = 0.0
        
        # 当前表情
        self.current_expression = "default"
        
        # 初始化
        if LIV2D_AVAILABLE:
            self._init_live2d()
        else:
            logger.error("live2d-py 不可用，无法加载 Live2D 模型")
            
    def _init_live2d(self):
        """初始化 Live2D"""
        try:
            # 初始化内存分配器
            live2d.init()
            logger.info("Live2D 内存分配器初始化完成")
            
            # 查找模型 JSON 文件
            model_json_paths = [
                self.model_dir / "ugofficial.model3.json",
                self.model_dir / "UGOfficial.model3.json",
                self.model_dir / "model.json",
            ]
            
            model_json_path = None
            for path in model_json_paths:
                if path.exists():
                    model_json_path = str(path.resolve())
                    break
            
            if model_json_path is None:
                logger.error(f"未找到模型 JSON 文件! 搜索路径: {self.model_dir}")
                return
            
            logger.info(f"找到模型配置: {model_json_path}")
            
            # 创建模型实例
            self.model = Model()
            
            # 加载模型
            self.model.LoadModelJson(model_json_path)
            logger.info("模型文件加载完成")
            
            # 获取模型画布大小
            canvas_size = self.model.GetCanvasSize()
            logger.info(f"模型画布尺寸: {canvas_size}")
            
            # 检查是否需要 OpenGL 初始化
            if self.needs_opengl_init:
                logger.info("等待 OpenGL 上下文初始化后再创建渲染器")
                self.model_loaded = True
                return
            
            # 创建渲染器
            self._create_renderer()
            
            self.model_loaded = True
            logger.info("Live2D 模型加载成功!")
            
        except Exception as e:
            logger.error(f"Live2D 初始化失败: {e}", exc_info=True)
            self.model_loaded = False

    def _create_renderer(self):
        """创建渲染器"""
        if not self.model:
            return
            
        try:
            # 初始化 OpenGL
            live2d.glInit()
            logger.info("Live2D OpenGL 初始化完成")
            
            # 创建渲染器
            self.model.CreateRenderer(maskBufferCount=2)
            logger.info("渲染器创建完成")
            
            # 启用自动呼吸
            self.model.SetAutoBreath(True)
            
            # 启用自动眨眼
            self.model.SetAutoBlink(True)
            
            # 设置显示参数
            self._calculate_display_params(self.model.GetCanvasSize())
            
            # 开始待机动作
            self._start_idle_motion()
            
            self.renderer_ready = True
            logger.info("渲染器就绪!")
            
        except Exception as e:
            logger.error(f"渲染器创建失败: {e}", exc_info=True)

    def finalize_init(self):
        """完成初始化（调用时需要有 OpenGL 上下文）"""
        if self.model_loaded and not self.renderer_ready:
            self.needs_opengl_init = False
            self._create_renderer()

    def _calculate_display_params(self, canvas_size: tuple):
        """计算显示参数"""
        if not canvas_size or canvas_size[0] == 0:
            return
            
        canvas_w, canvas_h = canvas_size
        
        # 计算缩放比例，使模型适应窗口
        scale_x = self.view_width / canvas_w
        scale_y = self.view_height / canvas_h
        self.scale = min(scale_x, scale_y) * 0.85
        
        # 居中偏移
        self.offset_x = 0.0
        self.offset_y = (self.view_height / canvas_h - self.scale) * canvas_h / 2
        
        logger.info(f"显示参数: scale={self.scale:.4f}, offset=({self.offset_x:.1f}, {self.offset_y:.1f})")

    def _start_idle_motion(self):
        """开始待机动作"""
        if not self.model or not self.renderer_ready:
            return
            
        try:
            # 尝试播放默认动作组
            motions = self.model.GetMotions()
            if motions:
                for group_name in motions.keys():
                    self.model.StartRandomMotion(group_name, priority=1)
                    logger.info(f"开始动作组: {group_name}")
                    break
        except Exception as e:
            logger.warning(f"无法播放待机动作: {e}")

    def set_expression(self, expression_id: str, fade_time: float = -1.0):
        """设置表情"""
        if not self.model or not self.model_loaded:
            return
            
        try:
            # 处理表达式ID（移除扩展名）
            if expression_id.endswith('.exp3.json'):
                expression_id = expression_id[:-9]
                
            self.model.SetExpression(expression_id)
            self.current_expression = expression_id
            logger.info(f"表情设置: {expression_id}")
        except Exception as e:
            logger.warning(f"表情设置失败: {e}")

    def set_random_expression(self):
        """设置随机表情"""
        if not self.model or not self.model_loaded:
            return
            
        try:
            expr_id = self.model.SetRandomExpression()
            if expr_id:
                self.current_expression = expr_id
                logger.info(f"随机表情: {expr_id}")
        except Exception as e:
            logger.warning(f"随机表情设置失败: {e}")

    def start_motion(self, group: str, index: int = -1, priority: int = 3):
        """播放动作"""
        if not self.model or not self.model_loaded:
            return
            
        try:
            if index < 0:
                self.model.StartRandomMotion(group, priority=priority)
                logger.info(f"播放随机动作: {group}")
            else:
                self.model.StartMotion(group, index, priority=priority)
                logger.info(f"播放动作: {group}[{index}]")
        except Exception as e:
            logger.warning(f"动作播放失败: {e}")

    def set_drag(self, x: float, y: float):
        """设置拖拽"""
        self.drag_x = x
        self.drag_y = y
        
        if self.model and self.model_loaded:
            try:
                self.model.Drag(x, y)
            except:
                pass

    def update(self, dt: float, mouse_x: float, mouse_y: float):
        """更新动画"""
        self.mouse_x = mouse_x
        self.mouse_y = mouse_y
        
        if not self.model or not self.model_loaded:
            return
            
        # 更新呼吸动画
        self.breath_phase += dt * 1.5
        self.hover_phase += dt * 0.8
        self.hover_offset = math.sin(self.hover_phase) * 3

    def update_model(self, dt: float):
        """更新模型状态（每帧调用）"""
        if not self.model or not self.model_loaded:
            return False
            
        try:
            self.model.Update(dt)
            return True
        except Exception as e:
            logger.warning(f"模型更新失败: {e}")
            return False

    def draw(self):
        """渲染模型"""
        if not self.model or not self.renderer_ready:
            return
            
        try:
            # 启用 OpenGL 混合
            from OpenGL.GL import glEnable, glBlendFunc, GL_BLEND, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            
            # 渲染模型
            self.model.Draw()
            
        except Exception as e:
            logger.warning(f"模型渲染失败: {e}")

    def get_rect(self) -> tuple:
        """获取碰撞区域"""
        # 返回基于模型的碰撞区域
        return (0, 0, self.view_width, self.view_height)
    
    def get_rect_with_hover(self) -> tuple:
        """获取包含悬浮偏移的碰撞区域"""
        x, y, w, h = self.get_rect()
        return (x, y + int(self.hover_offset), w, h)

    def hit_test(self, x: float, y: float) -> bool:
        """点击测试"""
        if not self.model or not self.model_loaded:
            return False
            
        try:
            return self.model.HitPart(x, y, topOnly=True)
        except:
            return False

    def dispose(self):
        """释放资源"""
        if self.model and self.model_loaded:
            try:
                self.model.DestroyRenderer()
                logger.info("Live2D 渲染器已销毁")
            except:
                pass
                
        if LIV2D_AVAILABLE:
            try:
                live2d.glRelease()
                live2d.dispose()
                logger.info("Live2D 已释放")
            except:
                pass


class Live2DWrapper:
    """兼容性别名 - 提供统一接口"""

    def __init__(self, model_dir: str, init_opengl: bool = False):
        self.renderer = CubismLive2DRenderer(model_dir, init_opengl)
        self.model_loaded = self.renderer.model_loaded
        
    def set_expression(self, name: str, duration: float = 3.0):
        """设置表情"""
        self.renderer.set_expression(name, duration)
        
    def reset_expression(self):
        """重置表情"""
        if self.renderer.model and self.renderer.model_loaded:
            self.renderer.model.ResetExpression()
            
    def update(self, dt: float, mouse_x: float, mouse_y: float):
        """更新"""
        self.renderer.update(dt, mouse_x, mouse_y)
        
    def render(self, screen):
        """渲染（仅更新模型，屏幕渲染由外部 OpenGL 处理）"""
        self.renderer.update_model(1/60)
        self.renderer.draw()
        
    def get_rect(self):
        """获取区域"""
        return self.renderer.get_rect()
    
    def get_rect_with_hover(self):
        """获取区域（含悬浮）"""
        return self.renderer.get_rect_with_hover()
    
    def is_blinking(self):
        """眨眼状态（兼容）"""
        return False
    
    def blink_duration(self):
        """眨眼持续时间（兼容）"""
        return 0.0


class ExpressionManager:
    """表情管理器"""

    def __init__(self, model_dir: str):
        self.model_dir = Path(model_dir)
        self.expressions = [
            "1desk", "2mic", "3clever", "4OAO", "5QAQ",
            "6i gi a ri", "7keyboard", "8punch", "9"
        ]

    def get_random_expression(self) -> str:
        """获取随机表情"""
        return random.choice(self.expressions)

    def get_expression_params(self, name: str) -> dict:
        """获取表情参数"""
        return {}


# 导出别名
Live2DRenderer = Live2DWrapper
