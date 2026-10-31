# CLAUDE.md - 麦麦祝你生日快乐呀 (geffnt_maibot-birthday-plugin)

## 1. 模块定位与系统职责
- **插件标识符**：`geffnt_maibot-birthday-plugin`
- **当前生效版本**：`v1.3.2`
- **托管仓库**：[`Wenaixi/maibot-birthday-plugin`](https://github.com/Wenaixi/maibot-birthday-plugin)
- **核心定位**：识别群成员生日名片，当天主动送上生日祝福，并把生日信息注入麦麦回复上下文。

## 2. 关键工程规范与配置说明
- **配置路径**：`config.toml`（所有业务调优与鉴权参数收敛于此）；
- **数据持久化**：优先遵循 MaiBot SDK 标准持久化规范，不直接向源码目录写入易失数据；
- **编码与日志规范**：严格遵循 PEP 8 风格，文档与代码注释杜绝 emoji，避免虚假套话。

## 3. 本地深度定制与稳定性修复
本地建立 Git 版本仓库，对齐主人 GitHub 远程库 Wenaixi/maibot-birthday-plugin。

---

## 上游项目与开源溯源
- **原作者 / 组织**：`geffnt`
- **官方上游仓库**：[https://github.com/geffnt/maibot-birthday-plugin](https://github.com/geffnt/maibot-birthday-plugin)
- **开源许可证**：`MIT`
- **分支演进模式**：本仓库作为主人的深度定制与生产维护分支（`Wenaixi/maibot-birthday-plugin`）。在保持与官方上游架构演进对齐的同时，锁死并持续维护针对本服务器生产环境的稳定性补丁与核心特性。
