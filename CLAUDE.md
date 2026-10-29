# 生日插件（geffnt_maibot-birthday-plugin）

## 官方上游与版本溯源
- 官方仓库（Upstream Repository）：https://github.com/geffnt/maibot-birthday-plugin
- 官方作者（Author / Maintainer）：geffnt
- 功能定位：MaiBot 生日记录、提前预告、主动祝福与回复上下文注入插件。
- 本地演进定位：基于官方上游最新版本，融入本地生产环境受众白名单隔离、频次配额控制与防抖冷却机制。
- 本地专属定制：
  1. 会话作用域解析（core/scope.py）：识别 group:xxx, qq:group:xxx, direct:xxx, private:xxx 等多样会话，提取当前作用域；
  2. 受众过滤（filter_people_for_scope）：仅在寿星本人所在群或与寿星私聊时才注入生日提示词，杜绝全群广播污染；
  3. 频次配额与冷却守护（core/quota.py）：支持单人单日最大祝福注入次数（max_greetings_per_day，默认 2 次）与防抖冷却时间（cooldown_seconds，默认 300.0s），消除无界念叨。

## 核心配置项说明（[prompt]）
- `enabled`：是否开启大模型回复前置注入；
- `max_greetings_per_day`：单个寿星在单个群/会话中每日最多注入祝福提示词的次数（默认 2）；
- `cooldown_seconds`：同一个人连续注入祝福提示词的最小间隔秒数（默认 300.0，5 分钟）。

## 验证与测试套件
- 单元测试：`tests/test_birthday_prompt_refactor.py`
- 端到端集成测试：`tests/test_plugin_integration.py`
- 运行命令：`python -m unittest -v tests/test_birthday_prompt_refactor.py tests/test_plugin_integration.py`（10 项，2026-10-27 全绿）

## birthday_query 工具范围化（2026-10-27 新增定制）
- 背景：10-27 生产日志实证 birthday_query 工具被 Planner 在 9 个群调用，无关键词时返回全库寿星名单，跨群泄漏直接导致麦麦在任意群念叨生日（如《刘华大哥群》说出其他群寿星）。
- 改造：
  1. `_resolve_tool_scope(kwargs)`：优先取宿主注入的 group_id，退而求其次 session_id/stream_id 推导（宿主 component_query.py:800-845 会把 stream_id/chat_id/group_id/user_id/platform 注入普通 @Tool 的 kwargs）；
  2. `_in_scope(person, scope_type, scope_id)`：群分支查 groups 列表、私聊分支比 user_id/key，不校验生日日期；
  3. `handle_birthday_query` 无关键词走 `_scoped_today_summary(scope_type, scope_id)`，有关键词搜索后过滤 `_in_scope`，无范围时绝不输出名单；
  4. `_scoped_today_summary` 与注入器共享 `quota_tracker`（同一寿星当日配额/冷却两边同时记账），配额耗尽只提示已祝福不点名；未来 7 天预告同样按范围过滤。
- 测试：tests/test_plugin_integration.py 新增 4 个用例覆盖跨群隔离、配额共享、关键词范围化、未知范围零泄漏。
