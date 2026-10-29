"""MaiBot 生日插件深度重构专项自动化测试套件。

涵盖核心场景：
1. 群聊寿星精准注入：当前群存在今天过生日的群友，正常注入提示；
2. 跨群隔离守卫：寿星在群 A，当前为群 B，绝不注入任何内容；
3. 频次配额限制：同一寿星当日提示次数达到上限（默认 2 次）后自动收手；
4. 冷却防抖守卫：两次注入之间受冷却时间约束，短时间内连续对话不频繁复读；
5. 私聊定向隔离：私聊会话仅对寿星本人注入，其他私聊对象绝不提及；
6. 多寿星独立记账：群内多位寿星各自记账，互不干扰。
"""

import sys
import unittest
from datetime import date
from pathlib import Path

# 确保能导入待测模块
plugin_dir = Path(__file__).resolve().parent.parent
if str(plugin_dir) not in sys.path:
    sys.path.insert(0, str(plugin_dir))


class MockLogger:
    def debug(self, msg, *args): pass
    def info(self, msg, *args): pass
    def warning(self, msg, *args): pass
    def error(self, msg, *args): pass


class TestBirthdayPromptRefactor(unittest.TestCase):
    """测试生日提醒会话感知与频次控制逻辑。"""

    def setUp(self):
        # 准备测试数据
        self.today = date.today()
        self.people = {
            "10001": {
                "key": "10001",
                "user_id": "10001",
                "name": "寿星小明",
                "month": self.today.month,
                "day": self.today.day,
                "year": 2000,
                "groups": ["group_A", "group_Shared"],
                "is_friend": True,
            },
            "10002": {
                "key": "10002",
                "user_id": "10002",
                "name": "寿星小红",
                "month": self.today.month,
                "day": self.today.day,
                "year": 2001,
                "groups": ["group_B"],
                "is_friend": False,
            },
            "10003": {
                "key": "10003",
                "user_id": "10003",
                "name": "平日群友小刚",
                "month": (self.today.month % 12) + 1,
                "day": 15,
                "year": 1999,
                "groups": ["group_A", "group_B"],
                "is_friend": True,
            },
        }

    def test_session_id_resolver(self):
        """测试 session_id 解析群号和用户号。"""
        from core.scope import resolve_session_scope

        # 测试各种群聊 session_id 格式
        self.assertEqual(resolve_session_scope("group:123456"), ("group", "123456"))
        self.assertEqual(resolve_session_scope("qq:group:123456"), ("group", "123456"))
        self.assertEqual(resolve_session_scope("group_123456"), ("group", "123456"))
        self.assertEqual(resolve_session_scope("123456"), ("group", "123456"))

        # 测试私聊 session_id 格式
        self.assertEqual(resolve_session_scope("private:987654"), ("private", "987654"))
        self.assertEqual(resolve_session_scope("qq:private:987654"), ("private", "987654"))
        self.assertEqual(resolve_session_scope("direct:987654"), ("private", "987654"))

        # 测试空或异常
        self.assertEqual(resolve_session_scope(""), ("unknown", ""))

    def test_filter_birthday_people_for_session(self):
        """测试按会话精准筛选今天过生日的人。"""
        from core.scope import filter_people_for_scope

        # 群 A：只有小明在群 A，小红不在群 A，小刚今天不过生日
        matched_a = filter_people_for_scope(self.people.values(), scope_type="group", scope_id="group_A")
        self.assertEqual([p["name"] for p in matched_a], ["寿星小明"])

        # 群 B：只有小红在群 B
        matched_b = filter_people_for_scope(self.people.values(), scope_type="group", scope_id="group_B")
        self.assertEqual([p["name"] for p in matched_b], ["寿星小红"])

        # 群 C：既没有小明也没有小红
        matched_c = filter_people_for_scope(self.people.values(), scope_type="group", scope_id="group_C")
        self.assertEqual(matched_c, [])

        # 私聊 10001（小明本人）：匹配到小明
        matched_p1 = filter_people_for_scope(self.people.values(), scope_type="private", scope_id="10001")
        self.assertEqual([p["name"] for p in matched_p1], ["寿星小明"])

        # 私聊 10003（小刚，今天不过生日）：匹配不到
        matched_p2 = filter_people_for_scope(self.people.values(), scope_type="private", scope_id="10003")
        self.assertEqual(matched_p2, [])

    def test_frequency_quota_and_cooldown(self):
        """测试同一寿星的祝福频次配额（默认2次）与冷却防抖。"""
        from core.quota import BirthdayQuotaTracker

        tracker = BirthdayQuotaTracker(max_greetings_per_person=2, cooldown_seconds=300)

        # 第 1 次在 group_A 为小明(10001)检查配额：应该放行
        can_greet, reason = tracker.can_inject(user_key="10001", scope_id="group_A", now=1000.0)
        self.assertTrue(can_greet)
        # 记录第 1 次注入成功
        tracker.record_injected(user_key="10001", scope_id="group_A", now=1000.0)

        # 10 秒后（未过冷却 300 秒）：应该被冷却拦截
        can_greet_cd, reason_cd = tracker.can_inject(user_key="10001", scope_id="group_A", now=1010.0)
        self.assertFalse(can_greet_cd)
        self.assertIn("cooldown", reason_cd)

        # 301 秒后（过了冷却）：第 2 次应该放行
        can_greet_2, reason_2 = tracker.can_inject(user_key="10001", scope_id="group_A", now=1301.0)
        self.assertTrue(can_greet_2)
        # 记录第 2 次注入成功
        tracker.record_injected(user_key="10001", scope_id="group_A", now=1301.0)

        # 再次过了冷却（例如 2000 秒后）：此时达到今日配额上限 2 次，应该被配额拦截
        can_greet_3, reason_3 = tracker.can_inject(user_key="10001", scope_id="group_A", now=2000.0)
        self.assertFalse(can_greet_3)
        self.assertIn("quota_reached", reason_3)

    def test_multi_person_quota_independence(self):
        """测试不同人之间的配额互不影响。"""
        from core.quota import BirthdayQuotaTracker

        tracker = BirthdayQuotaTracker(max_greetings_per_person=2, cooldown_seconds=300)

        # 小明在 group_Shared 消耗全部 2 次配额
        tracker.record_injected("10001", "group_Shared", now=1000.0)
        tracker.record_injected("10001", "group_Shared", now=1400.0)
        self.assertFalse(tracker.can_inject("10001", "group_Shared", now=2000.0)[0])

        # 此时小红(10002)应该完全不受影响，仍可以正常祝福
        can_greet_hong, _ = tracker.can_inject("10002", "group_Shared", now=2000.0)
        self.assertTrue(can_greet_hong)


if __name__ == "__main__":
    unittest.main()