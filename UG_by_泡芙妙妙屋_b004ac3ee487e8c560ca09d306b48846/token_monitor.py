"""
Token 用量监控系统
跟踪 API 调用的 Token 消耗，管理每日预算
"""

import json
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

from config import DAILY_TOKEN_BUDGET, TOKEN_WARNING_THRESHOLD, TOKEN_EXHAUSTED_THRESHOLD

logger = logging.getLogger(__name__)


class TokenMonitor:
    """Token 用量监控"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.stats_file = self.data_dir / "token_stats.json"

        self.daily_budget = DAILY_TOKEN_BUDGET
        self.today_date: Optional[str] = None

        # 当日统计
        self.input_tokens = 0
        self.output_tokens = 0
        self.call_count = 0
        self.error_count = 0

        # 是否进入精简模式
        self.economy_mode = False

        self._load_or_reset()

    def _get_today_str(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _load_or_reset(self):
        """加载或重置今日统计数据"""
        today = self._get_today_str()
        
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                saved_date = data.get("date", "")
                if saved_date == today:
                    # 同一天，加载已有数据
                    self.input_tokens = data.get("input_tokens", 0)
                    self.output_tokens = data.get("output_tokens", 0)
                    self.call_count = data.get("call_count", 0)
                    self.error_count = data.get("error_count", 0)
                    self.today_date = today
                    logger.info(f"Token统计已加载: 今日已使用 {self.total_tokens}")
                    return
            except Exception as e:
                logger.warning(f"加载Token统计失败: {e}")

        # 新的一天或加载失败，重置
        self._reset_daily(today)

    def _reset_daily(self, date: str):
        """重置日统计"""
        old_total = self.input_tokens + self.output_tokens
        self.input_tokens = 0
        self.output_tokens = 0
        self.call_count = 0
        self.error_count = 0
        self.today_date = date
        self.economy_mode = False
        logger.info(f"新的一天({date})，Token统计已重置。昨日总计: {old_total}")

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def usage_percent(self) -> float:
        if self.daily_budget == 0:
            return 100.0
        return self.total_tokens / self.daily_budget * 100

    def record_call(self, input_tokens: int, output_tokens: int, error: bool = False):
        """
        记录一次 API 调用
        
        Args:
            input_tokens: 输入 Token 数
            output_tokens: 输出 Token 数
            error: 是否出错
        """
        # 检查日期变更
        today = self._get_today_str()
        if today != self.today_date:
            self._reset_daily(today)

        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.call_count += 1
        if error:
            self.error_count += 1

        # 检查预算状态
        usage_pct = self.usage_percent
        if usage_pct >= TOKEN_EXHAUSTED_THRESHOLD and not self.economy_mode:
            self.economy_mode = True
            logger.warning(f"⚠️ Token预算已耗尽({usage_pct:.1f}%)，切换到精简模式")
        elif usage_pct >= TOKEN_WARNING_THRESHOLD:
            logger.warning(f"⚠️ Token用量已达 {usage_pct:.1f}%，请注意控制")

        # 记录日志
        logger.info(
            f"API调用 #{self.call_count}: "
            f"+{input_tokens}/+{output_tokens} tokens | "
            f"总计: {self.total_tokens:,} ({usage_pct:.1f}%)"
        )

        self._save()

    def should_use_api(self) -> bool:
        """
        判断是否应该调用 API
        
        Returns:
            True 如果可以调用 API
        """
        if self.economy_mode:
            # 精简模式下只有20%概率调用 API
            return False
        return True

    def get_warning_message(self) -> Optional[str]:
        """
        获取警告消息（如果应该显示）
        
        Returns:
            警告消息文本或 None
        """
        pct = self.usage_percent
        if pct >= TOKEN_EXHAUSTED_THRESHOLD:
            return "今天说了好多话，有点累了...先休息一下吧(´;ω;`)"
        elif pct >= TOKEN_WARNING_THRESHOLD:
            return "今天已经说了好多话啦，还有一点点额度哦～"
        return None

    def get_status_string(self) -> str:
        """获取当前状态字符串"""
        pct = self.usage_percent
        mode_str = " [精简模式]" if self.economy_mode else ""
        return (
            f"📊 Token 用量\n"
            f"输入: {self.input_tokens:,}\n"
            f"输出: {self.output_tokens:,}\n"
            f"总消耗: {self.total_tokens:,} / {self.daily_budget:,} ({pct:.1f}%)\n"
            f"调用次数: {self.call_count}{mode_str}"
        )

    def _save(self):
        """保存到文件"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "date": self.today_date,
                    "input_tokens": self.input_tokens,
                    "output_tokens": self.output_tokens,
                    "call_count": self.call_count,
                    "error_count": self.error_count,
                    "daily_budget": self.daily_budget,
                    "economy_mode": self.economy_mode,
                    "last_updated": datetime.now().isoformat(),
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存Token统计失败: {e}")
