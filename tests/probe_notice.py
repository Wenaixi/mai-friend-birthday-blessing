
import sys, os
from datetime import date
from unittest.mock import MagicMock
import types

plugin_dir = 'Maibot-new/plugins/geffnt_maibot-birthday-plugin'
sys.path.insert(0, plugin_dir)

import pydantic
sdk_mock = types.ModuleType("maibot_sdk")
sdk_mock.MaiBotPlugin = type("MaiBotPlugin", (), {})
sdk_mock.PluginConfigBase = pydantic.BaseModel
sdk_mock.CONFIG_RELOAD_SCOPE_SELF = "self"
def dummy_dec(*args, **kwargs):
    def wrapper(f): return f
    return wrapper
sdk_mock.HookHandler = dummy_dec
sdk_mock.Tool = dummy_dec
sdk_mock.Command = dummy_dec
sdk_mock.API = dummy_dec
sdk_mock.Field = pydantic.Field
sys.modules["maibot_sdk"] = sdk_mock

types_mock = types.ModuleType("maibot_sdk.types")
types_mock.ErrorPolicy = type("ErrorPolicy", (), {"SKIP": "skip"})
types_mock.HookMode = type("HookMode", (), {"BLOCKING": "blocking"})
types_mock.HookOrder = type("HookOrder", (), {"LATE": "late"})
class MockToolParameterInfo:
    def __init__(self, *args, **kwargs): pass
types_mock.ToolParameterInfo = MockToolParameterInfo
types_mock.ToolParamType = type("ToolParamType", (), {"STRING": "string"})
sys.modules["maibot_sdk.types"] = types_mock

from plugin import BirthdayPlugin, BirthdayConfig
from core.scope import resolve_session_scope, filter_people_for_scope

p = BirthdayPlugin()
p._ready = True
p.config = BirthdayConfig()
p.ctx = MagicMock()
p.ctx.logger = MagicMock()

today = date.today()
person_ming = {
    "key": "user:11111",
    "user_id": "11111",
    "name": "小明",
    "month": today.month,
    "day": today.day,
    "groups": ["1001"],
}
mock_store = MagicMock()
mock_store.people_on.return_value = [person_ming]
mock_store.was_greeted.return_value = False
mock_store.upcoming.return_value = []
p._store = mock_store

st, si = resolve_session_scope("group:1001")
print("Scope resolved:", st, si)
notice = p._build_prompt_notice(scope_type=st, scope_id=si)
print("Notice:", repr(notice))
