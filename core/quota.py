"""MaiBot 生日祝福频次配额与冷却防抖追踪器。

彻底解决生日提示无限复读问题：
1. 寿星配额控制：每位寿星当日最多被注入/祝福 N 次（默认 1~2 次）；
2. 冷却时间防抖：两次提示之间受 cooldown_seconds 约束，短时间内连续回复不刷屏；
3. 自动跨天清零与过期清理。
"""

import time
from datetime import date
from typing import Any, Dict, Tuple, Optional


class BirthdayQuotaTracker:
    """生日提醒频次配额与冷却控制器。"""

    def __init__(
        self,
        max_greetings_per_person: int = 2,
        cooldown_seconds: float = 300.0,
        initial_records: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.max_greetings_per_person = max(1, int(max_greetings_per_person))
        self.cooldown_seconds = max(0.0, float(cooldown_seconds))
        # 结构: { "YYYY-MM-DD": { "user_key": { "count": int, "last_at": float, "scopes": list[str] } } }
        self._records: Dict[str, Dict[str, Dict[str, Any]]] = {}
        if isinstance(initial_records, dict):
            self.load_state(initial_records)

    @staticmethod
    def _get_today_str(today: Optional[date] = None) -> str:
        return (today or date.today()).strftime("%Y-%m-%d")

    def can_inject(
        self,
        user_key: str,
        scope_id: str,
        now: Optional[float] = None,
        today: Optional[date] = None,
    ) -> Tuple[bool, str]:
        """检查某位寿星当前是否允许被注入提示词。

        返回: (allowed: bool, reason: str)
            reason 可选值: "ok" | "quota_reached" | "cooldown_active"
        """
        key = str(user_key).strip()
        if not key:
            return False, "invalid_user_key"

        current_time = float(now if now is not None else time.time())
        day_str = self._get_today_str(today)
        day_records = self._records.get(day_str, {})
        user_record = day_records.get(key)

        if not user_record:
            return True, "ok"

        count = int(user_record.get("count") or 0)
        if count >= self.max_greetings_per_person:
            return False, f"quota_reached (count={count} >= max={self.max_greetings_per_person})"

        last_at = float(user_record.get("last_at") or 0.0)
        elapsed = current_time - last_at
        if elapsed < self.cooldown_seconds:
            remaining = int(self.cooldown_seconds - elapsed)
            return False, f"cooldown_active (remaining={remaining}s)"

        return True, "ok"

    def record_injected(
        self,
        user_key: str,
        scope_id: str,
        now: Optional[float] = None,
        today: Optional[date] = None,
    ) -> int:
        """记录一次对寿星的提示词注入，返回该寿星今日累计次数。"""
        key = str(user_key).strip()
        if not key:
            return 0

        current_time = float(now if now is not None else time.time())
        day_str = self._get_today_str(today)

        if day_str not in self._records:
            self._records[day_str] = {}

        day_dict = self._records[day_str]
        record = day_dict.setdefault(
            key,
            {"count": 0, "last_at": 0.0, "scopes": []},
        )

        record["count"] = int(record.get("count") or 0) + 1
        record["last_at"] = current_time

        scope_str = str(scope_id).strip()
        if scope_str and scope_str not in record.get("scopes", []):
            record.setdefault("scopes", []).append(scope_str)

        return record["count"]

    def try_inject(
        self,
        user_key: str,
        scope_id: str,
        now: Optional[float] = None,
        today: Optional[date] = None,
    ) -> bool:
        """检查并原子记账一次对寿星的提示词注入。
        
        如果允许注入，记账并返回 True；如果处于冷却中或已达配额上限，返回 False。
        """
        allowed, _ = self.can_inject(user_key, scope_id, now=now, today=today)
        if not allowed:
            return False
        self.record_injected(user_key, scope_id, now=now, today=today)
        return True

    def export_state(self) -> Dict[str, Any]:
        """导出当前配额状态用于持久化。"""
        return {"records": self._records}

    def load_state(self, state: Dict[str, Any]) -> None:
        """从持久化字典加载配额状态，自动丢弃 7 天前的历史。"""
        if not isinstance(state, dict):
            return
        records = state.get("records")
        if not isinstance(records, dict):
            return

        cutoff = (date.today().toordinal() - 7)
        self._records = {}

        for day_str, day_data in records.items():
            try:
                parts = [int(p) for p in day_str.split("-")]
                d = date(parts[0], parts[1], parts[2])
                if d.toordinal() >= cutoff and isinstance(day_data, dict):
                    self._records[day_str] = {
                        str(k): v for k, v in day_data.items() if isinstance(v, dict)
                    }
            except Exception:
                continue
