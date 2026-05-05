"""
记忆管理系统
包含短期记忆（会话内）、长期记忆（文件存储）和好感度系统
"""

import json
import os
import time
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from config import (
    INITIAL_AFFECTION, MAX_AFFECTION,
    AFFECTION_PER_CHAT, AFFECTION_PER_CLICK,
    AFFECTION_ONLINE_BONUS_HOUR, AFFECTION_IGNORE_PENALTY, IGNORE_THRESHOLD_HOURS
)

logger = logging.getLogger(__name__)


class MemoryManager:
    """记忆管理器"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # 文件路径
        self.long_term_memory_file = self.data_dir / "long_term_memory.json"
        self.affection_file = self.data_dir / "affection.json"
        self.daily_stats_file = self.data_dir / "daily_stats.json"

        # 短期记忆（内存中）
        self.short_term_memory: list[dict] = []  # 最近对话
        self.max_short_term = 15

        # 长期记忆
        self.long_term_memory: dict = {
            "user_info": {},      # 用户告诉我们的信息
            "milestones": [],     # 互动里程碑
            "preferences": {},    # 用户偏好
            "important_events": [],
        }

        # 好感度
        self.affection = INITIAL_AFFECTION
        self.affection_history: list[dict] = []

        # 统计
        self.start_time = time.time()
        self.last_interaction_time = time.time()
        self.total_chats = 0
        self.total_clicks = 0
        self.online_bonus_given_today: set = set()  # 已奖励的小时标记

        # 加载持久化数据
        self._load_data()

        logger.info(f"记忆系统初始化完成，当前好感度: {self.affection}")

    def _load_data(self):
        """从文件加载数据"""
        try:
            # 长期记忆
            if self.long_term_memory_file.exists():
                with open(self.long_term_memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.long_term_memory = {**self.long_term_memory, **data}
                logger.info("长期记忆加载成功")

            # 好感度
            if self.affection_file.exists():
                with open(self.affection_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.affection = min(data.get("affection", INITIAL_AFFECTION), MAX_AFFECTION)
                self.last_interaction_time = data.get("last_interaction", time.time())
                logger.info(f"好感度数据加载: {self.affection}")

        except Exception as e:
            logger.warning(f"加载记忆数据失败: {e}")

    def _save_data(self):
        """保存数据到文件"""
        try:
            with open(self.long_term_memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.long_term_memory, f, ensure_ascii=False, indent=2)

            with open(self.affection_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "affection": self.affection,
                    "last_interaction": self.last_interaction_time,
                    "updated": datetime.now().isoformat(),
                }, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存记忆数据失败: {e}")

    # ==================== 短期记忆 ====================

    def add_chat_to_memory(self, user_msg: str, assistant_msg: str):
        """添加对话到短期记忆"""
        self.short_term_memory.append({
            "role": "user",
            "content": user_msg,
            "timestamp": time.time(),
        })
        self.short_term_memory.append({
            "role": "assistant",
            "content": assistant_msg,
            "timestamp": time.time(),
        })

        # 限制长度
        if len(self.short_term_memory) > self.max_short_term * 2:
            self.short_term_memory = self.short_term_memory[-(self.max_short_term * 2):]

        self._on_chat()

    def get_context_for_llm(self) -> str:
        """获取给 LLM 的上下文摘要"""
        if not self.short_term_memory:
            return ""
        
        context_lines = []
        for msg in self.short_term_memory[-10:]:  # 最近10条消息
            role_label = "用户" if msg["role"] == "user" else "小U"
            context_lines.append(f"{role_label}: {msg['content']}")
        
        return "\n".join(context_lines)

    def clear_short_term(self):
        """清除短期记忆"""
        self.short_term_memory.clear()
        logger.info("短期记忆已清除")

    # ==================== 长期记忆 ====================

    def remember_user_info(self, key: str, value: str):
        """记住用户信息"""
        self.long_term_memory["user_info"][key] = value
        self.long_term_memory["milestones"].append({
            "type": "info_learned",
            "key": key,
            "time": datetime.now().isoformat(),
        })
        self._save_data()
        logger.info(f"记住用户信息: {key} = {value}")

    def add_milestone(self, milestone_type: str, description: str):
        """添加里程碑"""
        self.long_term_memory["milestones"].append({
            "type": milestone_type,
            "description": description,
            "time": datetime.now().isoformat(),
        })
        self._save_data()
        logger.info(f"添加里程碑: {description}")

    def record_preference(self, category: str, preference: str):
        """记录用户偏好"""
        if category not in self.long_term_memory["preferences"]:
            self.long_term_memory["preferences"][category] = []
        prefs = self.long_term_memory["preferences"][category]
        if preference not in prefs:
            prefs.append(preference)
            self._save_data()
            logger.info(f"记录偏好: {category} -> {preference}")

    def get_user_summary(self) -> str:
        """获取用户信息摘要（用于LLM prompt增强）"""
        info = self.long_term_memory.get("user_info", {})
        if not info:
            return ""
        
        parts = [f"我知道用户的一些信息:"]
        for k, v in info.items():
            parts.append(f"- {k}: {v}")
        return "\n".join(parts)

    # ==================== 好感度系统 ====================

    def _on_chat(self):
        """聊天时的好感度处理"""
        self.total_chats += 1
        self._change_affection(AFFECTION_PER_CHAT, "chat")
        self.last_interaction_time = time.time()
        self._check_online_bonus()
        self._save_data()

    def _on_click(self):
        """点击时的好感度处理"""
        self.total_clicks += 1
        self._change_affection(AFFECTION_PER_CLICK, "click")
        self.last_interaction_time = time.time()
        self._check_online_bonus()
        self._save_data()

    def _change_affection(self, delta: float, reason: str):
        """改变好感度"""
        old = self.affection
        self.affection = max(0, min(MAX_AFFECTION, self.affection + delta))
        self.affection_history.append({
            "old_value": old,
            "new_value": self.affection,
            "delta": delta,
            "reason": reason,
            "time": datetime.now().isoformat(),
        })
        logger.info(f"好感度变化: {old:.1f} -> {self.affection:.1f} ({reason:+.1f})")

    def _check_online_bonus(self):
        """检查在线时长奖励"""
        online_hours = int((time.time() - self.start_time) // 3600)
        hour_key = str(online_hours)
        if hour_key not in self.online_bonus_given_today:
            self.online_bonus_given_today.add(hour_key)
            self._change_affection(AFFECTION_ONLINE_BONUS_HOUR, f"online_{hour_key}h")
            logger.info(f"获得在线{hour_key}小时奖励")

    def check_ignore_penalty(self):
        """检查是否需要扣除忽略惩罚"""
        hours_since_last = (time.time() - self.last_interaction_time) / 3600
        if hours_since_last > IGNORE_THRESHOLD_HOURS:
            self._change_affection(AFFECTION_IGNORE_PENALTY, "ignored")
            self.last_interaction_time = time.time()
            self._save_data()
            logger.warning(f"用户长时间未交互，好感度-2")

    def get_affection_level(self) -> str:
        """获取好感度等级描述"""
        if self.affection >= 90:
            return "超级亲密"
        elif self.affection >= 70:
            return "非常要好"
        elif self.affection >= 50:
            return "关系不错"
        elif self.affection >= 30:
            return "初次见面"
        else:
            return "有点陌生..."

    def get_affection_description(self) -> str:
        """获取好感度的完整描述文本"""
        level = self.get_affection_level()
        return f"好感度: {self.affection:.0f}/{MAX_AFFECTION} ({level})\n累计对话: {self.total_chats}次\n累计互动: {self.total_clicks}次"

    def is_new_day(self) -> bool:
        """检查是否是新的一天（首次启动问候用）"""
        stats_file = self.daily_stats_file
        today_str = datetime.now().strftime("%Y-%m-%d")

        try:
            if stats_file.exists():
                with open(stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                last_date = data.get("last_date", "")
                return last_date != today_str
        except Exception:
            pass
        
        return True

    def mark_today_started(self):
        """标记今天已启动"""
        with open(self.daily_stats_file, 'w', encoding='utf-8') as f:
            json.dump({"last_date": datetime.now().strftime("%Y-%m-%d")}, f)

    def get_greeting_message(self) -> Optional[str]:
        """获取每日首次启动的特别问候"""
        if self.is_new_day():
            self.mark_today_started()
            
            from config import PRESET_MESSAGES
            
            import datetime
            hour = datetime.datetime.now().hour
            
            if 5 <= hour < 12:
                messages = PRESET_MESSAGES.get("greeting_morning", [])
            elif 17 <= hour < 22 or 6 <= hour < 9:
                messages = ["主人晚上好呀～今天过得怎么样？(｡･ω･｡)", "回来啦！小U等你好久了～"]
            else:
                messages = PRESET_MESSAGES.get("greeting_night", [])
            
            # 根据好感度调整问候
            if self.affection >= 60:
                extra = "今天也要元气满满哦！"
            elif self.affection >= 30:
                extra = "要和我多聊聊天哦～"
            else:
                extra = ""
            
            base = random.choice(messages) if messages else "你好呀，主人！"
            return f"{base}\n{extra}" if extra else base

        return None



