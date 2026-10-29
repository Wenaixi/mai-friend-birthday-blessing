"""MaiBot 会话范围与受众判定模块。

负责从 MaiBot 的 session_id、stream_id 或 kwargs 中精准提取当前会话的群号或私聊号，
并根据寿星所属群/好友状态进行严格的会话范围过滤，杜绝跨群乱广播。
"""

import re
from datetime import date
from typing import Any, Iterable, Tuple, List, Dict, Optional


def resolve_session_scope(session_id: str, stream_id: str = "") -> Tuple[str, str]:
    """解析会话的类型与标识。
    
    返回: (scope_type, scope_id)
        scope_type: "group" | "private" | "unknown"
        scope_id: 群号字符串或用户 QQ 号字符串
    """
    raw = str(session_id or stream_id or "").strip()
    if not raw:
        return "unknown", ""

    # 1. 显式私聊格式：private:123456, qq:private:123456, direct:123456, private_123456
    m_private = re.search(r"(?:private|direct)[:_](\d+)", raw, re.IGNORECASE)
    if m_private:
        return "private", m_private.group(1)

    # 2. 显式群聊格式：group:123456, qq:group:123456, group_123456
    m_group = re.search(r"group[:_](\d+)", raw, re.IGNORECASE)
    if m_group:
        return "group", m_group.group(1)

    # 3. 纯数字提取：MaiBot 群聊 session_id 默认即为群号数字
    if raw.isdigit():
        return "group", raw

    # 4. 包含群号长数字的兜底匹配 (5~12位数字)
    m_any = re.search(r"(\d{5,12})", raw)
    if m_any:
        return "group", m_any.group(1)

    return "unknown", raw


def filter_people_for_scope(
    people: Iterable[Dict[str, Any]],
    scope_type: str,
    scope_id: str,
    today: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """根据当前会话范围，严格筛选属于当前受众且今天过生日的寿星列表。

    规则：
    1. 必须是今天过生日（如果指定了 today）：month == today.month and day == today.day；
    2. 群聊场景 (group): 寿星所属群列表 groups 中必须包含当前群号 scope_id；
    3. 私聊场景 (private): 寿星的 user_id 或 key 必须与当前私聊对象 scope_id 严格一致；
    4. 未知场景 (unknown): 为防止信息泄露和全网广播，默认不向未知场景注入寿星信息。
    """
    if not scope_id or scope_type == "unknown":
        return []

    target_date = today or date.today()
    target_month = target_date.month
    target_day = target_date.day

    matched = []
    scope_id_str = str(scope_id).strip()

    for person in people:
        if not isinstance(person, dict):
            continue

        # 检查是否今天过生日
        m = int(person.get("month") or 0)
        d = int(person.get("day") or 0)
        if m != target_month or d != target_day:
            continue

        # 检查是否属于当前会话范围
        if scope_type == "group":
            groups = [str(g).strip() for g in (person.get("groups") or [])]
            if scope_id_str in groups:
                matched.append(person)
        elif scope_type == "private":
            user_id = str(person.get("user_id") or person.get("key") or "").strip()
            if user_id == scope_id_str:
                matched.append(person)

    return matched
