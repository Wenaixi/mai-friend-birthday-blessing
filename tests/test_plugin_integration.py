"""MaiBot 生日插件端到端链路集成测试。

全面验证真实 BirthdayPlugin 类在群聊/私聊回复上下文注入、跨群隔离、频次配额和冷却防抖中的端到端行为。
"""

import sys
import os
import unittest
from datetime import date
from unittest.mock import MagicMock

# 确保能导入 mock 和测试目标
plugin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

# 模拟最小 maibot_sdk 环境
import types
if "maibot_sdk" not in sys.modules:
    sdk_mock = types.ModuleType("maibot_sdk")
    import pydantic
    sdk_mock.MaiBotPlugin = type("MaiBotPlugin", (), {})
    sdk_mock.PluginConfigBase = pydantic.BaseModel
    sdk_mock.CONFIG_RELOAD_SCOPE_SELF = "self"
    
    # 装饰器打桩
    def dummy_dec(*args, **kwargs):
        def wrapper(f):
            return f
        return wrapper

    sdk_mock.HookHandler = dummy_dec
    sdk_mock.Tool = dummy_dec
    sdk_mock.Command = dummy_dec
    sdk_mock.API = dummy_dec
    from pydantic import Field
    sdk_mock.Field = Field
    sys.modules["maibot_sdk"] = sdk_mock

if "maibot_sdk.types" not in sys.modules:
    types_mock = types.ModuleType("maibot_sdk.types")
    types_mock.ErrorPolicy = type("ErrorPolicy", (), {"SKIP": "skip"})
    types_mock.HookMode = type("HookMode", (), {"BLOCKING": "blocking"})
    types_mock.HookOrder = type("HookOrder", (), {"LATE": "late"})
    class MockToolParameterInfo:
        def __init__(self, *args, **kwargs):
            pass
    types_mock.ToolParameterInfo = MockToolParameterInfo
    types_mock.ToolParamType = type("ToolParamType", (), {"STRING": "string"})
    sys.modules["maibot_sdk.types"] = types_mock

# 导入插件主类
from plugin import BirthdayPlugin, BirthdayConfig


class TestBirthdayPluginIntegration(unittest.IsolatedAsyncioTestCase):
    """测试 BirthdayPlugin 的全链路行为。"""

    def setUp(self):
        self.plugin = BirthdayPlugin()
        self.plugin._ready = True
        self.plugin.config = BirthdayConfig()
        self.plugin.config.prompt.inject_prompt = True
        self.plugin.config.prompt.max_greetings_per_day = 2
        self.plugin.config.prompt.cooldown_seconds = 300.0

        # Mock 日志和存储
        self.plugin.ctx = MagicMock()
        self.plugin.ctx.logger = MagicMock()

        self.today = date.today()
        self.mock_store = MagicMock()

        # 模拟寿星数据：小明（群 1001），小红（群 2002）
        self.person_ming = {
            "key": "user:11111",
            "user_id": "11111",
            "name": "小明",
            "month": self.today.month,
            "day": self.today.day,
            "groups": ["1001"],
        }
        self.person_hong = {
            "key": "user:22222",
            "user_id": "22222",
            "name": "小红",
            "month": self.today.month,
            "day": self.today.day,
            "groups": ["2002"],
        }

        self.mock_store.people_on.return_value = [self.person_ming, self.person_hong]
        self.mock_store.was_greeted.return_value = False
        self.mock_store.upcoming.return_value = []
        self.plugin._store = self.mock_store

    async def test_group_isolation_and_quota_defense(self):
        """测试核心端到端功能：群隔离、冷却防抖和每日上限防刷。"""

        # 1. 麦麦在群 1001 中回复消息（第一次注入）
        res1 = await self.plugin.handle_replyer_before_request(
            session_id="group:1001",
            extra_prompt="原始系统提示词"
        )
        mod_prompt1 = res1.get("modified_kwargs", {}).get("extra_prompt", "")
        self.assertIn("小明", mod_prompt1, "群 1001 应该包含寿星小明的祝福提示")
        self.assertNotIn("小红", mod_prompt1, "群 1001 绝对不能包含属于群 2002 的小红！")

        # 2. 紧接着在群 1001 再次回复消息（未过 300 秒冷却）
        res2 = await self.plugin.handle_replyer_before_request(
            session_id="group:1001",
            extra_prompt="原始系统提示词"
        )
        mod_prompt2 = res2.get("modified_kwargs", {}).get("extra_prompt", "")
        self.assertEqual(mod_prompt2, "原始系统提示词", "冷却时间内应拦截注入，杜绝频繁念叨")

        # 3. 模拟时间推进 301 秒，再次在群 1001 回复（第二次注入，达到配额上限 2 次）
        record_key = self.person_ming["key"]
        day_str = self.today.strftime("%Y-%m-%d")
        self.plugin.quota_tracker._records[day_str][record_key]["last_at"] -= 305.0

        res3 = await self.plugin.handle_replyer_before_request(
            session_id="group:1001",
            extra_prompt="原始系统提示词"
        )
        mod_prompt3 = res3.get("modified_kwargs", {}).get("extra_prompt", "")
        self.assertIn("小明", mod_prompt3, "冷却结束后应允许注入第二次祝福")

        # 4. 再次推进时间 301 秒，第四次在群 1001 回复（已达 2 次配额上限）
        self.plugin.quota_tracker._records[day_str][record_key]["last_at"] -= 305.0
        res4 = await self.plugin.handle_replyer_before_request(
            session_id="group:1001",
            extra_prompt="原始系统提示词"
        )
        mod_prompt4 = res4.get("modified_kwargs", {}).get("extra_prompt", "")
        self.assertEqual(mod_prompt4, "原始系统提示词", "达到每日上限(2次)后，今天绝对不再提生日！")

        # 5. 此时切换到群 2002 回复（验证群隔离与小红独立配额）
        res_hong = await self.plugin.handle_replyer_before_request(
            session_id="group:2002",
            extra_prompt="原始系统提示词"
        )
        mod_prompt_hong = res_hong.get("modified_kwargs", {}).get("extra_prompt", "")
        self.assertIn("小红", mod_prompt_hong, "群 2002 应该能正常触发小红的祝福提示")
        self.assertNotIn("小明", mod_prompt_hong, "群 2002 绝对不能混入小明")

        # 6. 在一个没有任何寿星的普通群 3003 中回复
        res_other = await self.plugin.handle_replyer_before_request(
            session_id="group:3003",
            extra_prompt="原始系统提示词"
        )
        mod_prompt_other = res_other.get("modified_kwargs", {}).get("extra_prompt", "")
        self.assertEqual(mod_prompt_other, "原始系统提示词", "无寿星群绝对不修改提示词")



    async def test_private_session_isolation(self):
        """测试私聊场景下的定向注入与隔离。"""

        # 1. 小明私聊麦麦：session_id="private:11111"
        res_ming = await self.plugin.handle_replyer_before_request(
            session_id="private:11111",
            extra_prompt="私聊提示词"
        )
        mod_ming = res_ming.get("modified_kwargs", {}).get("extra_prompt", "")
        self.assertIn("小明", mod_ming, "私聊小明本人时应该注入小明的生日祝福")
        self.assertNotIn("小红", mod_ming, "私聊小明绝不能泄漏小红生日")

        # 2. 陌生人或非寿星小王私聊麦麦：session_id="private:99999"
        res_wang = await self.plugin.handle_replyer_before_request(
            session_id="private:99999",
            extra_prompt="私聊提示词"
        )
        mod_wang = res_wang.get("modified_kwargs", {}).get("extra_prompt", "")
        self.assertEqual(mod_wang, "私聊提示词", "非寿星私聊绝对不注入任何生日提示")

    async def test_birthday_query_group_scoped_and_quota_shared(self):
        """birthday_query 工具：只报当前群寿星，且与注入器共享每日配额/冷却。"""

        # 群 1001 查询：只出现小明
        res1 = await self.plugin.handle_birthday_query(group_id="1001")
        content1 = res1["content"]
        self.assertIn("小明", content1, "群 1001 查询应报出小明")
        self.assertNotIn("小红", content1, "群 1001 查询绝不能泄漏群 2002 的小红")

        # 冷却期内立刻再查：不再点名，提示已祝福
        res2 = await self.plugin.handle_birthday_query(group_id="1001")
        content2 = res2["content"]
        self.assertNotIn("小明", content2, "冷却期内不再重复点名小明")
        self.assertIn("祝福过了", content2, "冷却期内应提示已经祝福过")

        # 与注入器共享配额：注入器先在群 1001 提到小明 → 工具再查就被拦截
        await self.plugin.handle_replyer_before_request(
            session_id="group:1001", extra_prompt="原始系统提示词"
        )
        res3 = await self.plugin.handle_birthday_query(group_id="1001")
        self.assertNotIn("小明", res3["content"], "注入器消耗配额后工具查询不再点名小明")

    async def test_birthday_query_group_isolation_and_upcoming(self):
        """birthday_query 工具：跨群隔离 + 预告名单同样按群过滤。"""

        self.mock_store.upcoming.return_value = [(self.person_hong, 1)]
        res = await self.plugin.handle_birthday_query(group_id="2002")
        content = res["content"]
        self.assertIn("小红", content, "群 2002 查询应报出小红")
        self.assertNotIn("小明", content, "群 2002 查询绝不能泄漏小明")
        self.assertIn("小红", content, "群 2002 的预告应包含属于本群的小红")

        res_1001 = await self.plugin.handle_birthday_query(group_id="1001")
        self.assertNotIn("小红", res_1001["content"], "群 1001 的预告不能带群 2002 的小红")

    async def test_birthday_query_keyword_scoped(self):
        """birthday_query 工具：关键词搜索同样限定当前会话范围。"""

        self.mock_store.search.return_value = [self.person_ming, self.person_hong]
        res = await self.plugin.handle_birthday_query(group_id="1001", keyword="朋友")
        content = res["content"]
        self.assertIn("小明", content, "群 1001 内按关键词应匹配小明")
        self.assertNotIn("小红", content, "群 1001 内关键词匹配绝不能带出小红")

        res_2002 = await self.plugin.handle_birthday_query(group_id="2002", keyword="朋友")
        self.assertIn("小红", res_2002["content"], "群 2002 内按关键词应匹配小红")
        self.assertNotIn("小明", res_2002["content"], "群 2002 内关键词匹配绝不能带出小明")

    async def test_birthday_query_unknown_scope_no_leak(self):
        """birthday_query 工具：拿不到群/私聊范围时绝不输出任何名单。"""

        res = await self.plugin.handle_birthday_query()
        content = res["content"]
        self.assertNotIn("小明", content, "未知范围绝不能点名小明")
        self.assertNotIn("小红", content, "未知范围绝不能点名小红")

        # 关键词分支同样不泄漏
        self.mock_store.search.return_value = [self.person_ming, self.person_hong]
        res_kw = await self.plugin.handle_birthday_query(keyword="朋友")
        self.assertNotIn("小明", res_kw["content"], "未知范围带关键词也不能点名小明")
        self.assertNotIn("小红", res_kw["content"], "未知范围带关键词也不能点名小红")


if __name__ == "__main__":
    unittest.main()