"""
物理效果管理器
管理 Live2D 物理模拟（头发、衣服摆动等）
"""

import json
import math
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PhysicsManager:
    """
    Live2D 物理效果管理器
    
    解析 physics3.json 配置，实现简化的物理模拟
    """

    def __init__(self, model_dir: str):
        self.model_dir = Path(model_dir)
        self.physics_config: Optional[dict] = None
        self.particles: list[dict] = []
        self.wind_strength = 0.0
        self.time = 0.0

        self._load_physics()

    def _load_physics(self):
        """加载物理配置文件"""
        physics_path = self.model_dir / "UGOfficial.physics3.json"
        if physics_path.exists():
            try:
                with open(physics_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content.startswith('{'):
                        content = '{' + content
                    self.physics_config = json.loads(content)
                
                # 初始化粒子系统
                self._initialize_particles()
                logger.info(f"物理配置加载成功，{len(self.particles)} 个粒子")
            except Exception as e:
                logger.warning(f"物理配置加载失败: {e}")
                self.physics_config = None
        else:
            logger.warning(f"未找到物理配置: {physics_path}")

    def _initialize_particles(self):
        """从配置中初始化粒子"""
        if not self.physics_config:
            return
        
        settings_list = self.physics_config.get("Settings", [])
        for i, setting in enumerate(settings_list):
            particle = {
                "id": i,
                "name": setting.get("Id", f"particle_{i}"),
                # 基础参数
                "input": setting.get("Input", {}),
                "output": setting.get("Output", {}),
                "vertices": setting.get("Vertices", []),
                "position": setting.get("Position", {}),
                # 物理参数归一化
                "normalization": setting.get("Normalization", {}),
            }
            self.particles.append(particle)

    def update(self, delta_time: float, model_parameters: dict) -> dict[str, float]:
        """
        更新物理状态，返回需要修改的参数值
        
        Args:
            delta_time: 时间增量(秒)
            model_parameters: 当前模型参数字典
            
        Returns:
            参数更新字典 {param_name: value}
        """
        self.time += delta_time
        updates = {}

        # 如果没有加载到物理配置，使用默认的简化物理
        if not self.physics_config or not self.particles:
            return self._default_physics(updates)

        # 更新每个粒子
        for particle in self.particles:
            param_updates = self._update_particle(particle, delta_time, model_parameters)
            updates.update(param_updates)

        return updates

    def _default_physics(self, updates: dict) -> dict[str, float]:
        """
        默认简化物理效果（当没有 physics3.json 时使用）
        
        模拟头发/部件的自然摆动
        """
        t = self.time
        
        # 头发前摆动
        updates["ParamHairFrontFuwa"] = math.sin(t * 1.5) * 0.15 + math.sin(t * 3.7) * 0.05
        
        # 头发侧摆动
        updates["ParamHairSideFuwa"] = math.sin(t * 1.2 + 0.5) * 0.20 + math.cos(t * 2.9) * 0.06
        
        # 头发后摆动
        updates["ParamHairBackFuwa"] = math.sin(t * 0.9 + 1.0) * 0.25 + math.sin(t * 2.1) * 0.08

        # 风力影响
        if abs(self.wind_strength) > 0.01:
            wind_effect = self.wind_strength * 0.1
            updates["ParamHairFrontFuwa"] += wind_effect
            updates["ParamHairSideFuwa"] += wind_effect * 1.5
            updates["ParamHairBackFuwa"] += wind_effect * 2.0

        return updates

    def _update_particle(self, particle: dict, delta_time: float, 
                         model_params: dict) -> dict[str, float]:
        """
        更新单个粒子的物理状态
        
        简化的弹簧-阻尼物理系统
        """
        updates = {}
        
        # 获取输入参数
        input_info = particle.get("input", {})
        input_type = input_info.get("Source", {})
        source_param = input_type.get("Target", "")
        source_weight = input_info.get("Weight", 0)
        
        # 获取输入值
        source_value = 0.0
        if source_param and source_param in model_params:
            source_value = model_params[source_param]

        # 获取输出参数
        output_info = particle.get("output", [])
        
        # 简化物理计算：基于输入值和时间产生阻尼振荡
        for output in output_info:
            dest_param = output.get("Destination", "")
            if not dest_param:
                continue
            
            # 基础参数
            scale = output.get("Scale", 1.0)
            weight = output.get("Weight", 0)
            
            # 使用正弦波近似物理摆动
            base_freq = 1.5 + hash(dest_param) % 10 * 0.2  # 不同参数不同频率
            phase = hash(dest_param) % 100 / 100.0 * 3.14159
            
            # 输入影响 + 自然摆动
            natural_swing = math.sin(self.time * base_freq + phase) * scale * weight
            input_influence = source_value * source_weight * weight
            
            updates[dest_param] = natural_swing + input_influence * 0.3

        return updates

    def set_wind(self, strength: float):
        """
        设置风力强度
        
        Args:
            strength: 风力 (-1 到 1)，负=向左，正=向右
        """
        self.wind_strength = max(-1.0, min(1.0, strength))

    def reset(self):
        """重置物理状态"""
        self.time = 0.0
        self.wind_strength = 0.0
