# 麦麦祝你生日快乐呀

> 本插件由 [Wenaixi](https://github.com/Wenaixi) 维护，是专为生产环境深度调优的高可用分支。

## 简介与定位

识别群成员生日名片，寿星当天在群或私聊主动道贺，并将生日信息注入麦麦回复上下文。

- **插件目录**：`geffnt_maibot-birthday-plugin`
- **生效版本**：`v1.3.2`
- **开源许可证**：`MIT`

---

## 核心特性与本地深度调优

- 本地初始化独立 Git 仓库管理，对齐主人 GitHub 远程库

---

## 指令与工具速查

### 常用指令 (Command)
- `/birthday - 查询今日/近期寿星列表`

### 大模型工具 (Tool)
- `@Tool("birthday_query") - 查询群成员生日信息工具`

---

## 快速配置

配置文件统一定位于插件根目录下的 `config.toml`。修改后重启或通过 WebUI 热重载即可生效。

---

## 上游项目与开源溯源

- **原作者 / 组织**：`geffnt`
- **官方原版开源仓库**：[https://github.com/geffnt/maibot-birthday-plugin](https://github.com/geffnt/maibot-birthday-plugin)
- **开源协议**：`MIT`
- **声明**：本项目遵循开源协议，特此致敬原作者的杰出贡献。本分支针对生产环境的高并发网络、个性化社交和抗风控需求进行了深度稳定性修复与定制化演进。
