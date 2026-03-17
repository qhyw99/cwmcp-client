# 环境变量品牌前缀改造计划

## 目标
将项目内用于鉴权的环境变量从 `MCP_API_KEY` 统一升级为带品牌前缀的新名称，以便与其他工具区分。

## 命名决策
- 采用新变量名：`CONTEXTWEAVE_MCP_API_KEY`
- 迁移策略：代码先支持“新变量优先 + 旧变量兜底”，文档与配置默认仅展示新变量（并标注旧变量兼容期）

## 变更范围
- 运行时代码
  - `remote_mcp_server.py`
  - `cw-skill/scripts/cw_client.cjs`
  - `cw-skill/set_env.sh`
- 配置与元数据
  - `ContextWeave.json`
  - `cw-skill/_meta.json`
  - `cw-skill/SKILL.md` frontmatter
- 测试
  - `tests/test_client_billing.py`
- 文档
  - `README.md`

## 实施步骤
1. 在运行时代码中引入新变量名读取逻辑，顺序为：`CONTEXTWEAVE_MCP_API_KEY` → `MCP_API_KEY`。
2. 更新所有报错提示、引导文案和示例命令，默认指向 `CONTEXTWEAVE_MCP_API_KEY`。
3. 修改配置文件和 skill 元数据声明，将依赖变量名切换到 `CONTEXTWEAVE_MCP_API_KEY`。
4. 更新测试用例，覆盖“仅新变量可用”与“旧变量兼容”两条路径。
5. 更新 README 与 SKILL 文档，增加兼容说明与迁移提示，避免用户配置中断。

## 验证方案
- 静态检查：全仓搜索确认核心逻辑不再仅依赖 `MCP_API_KEY`。
- 自动化验证：执行与鉴权相关测试（重点 `tests/test_client_billing.py`）。
- 行为验证：
  - 仅设置 `CONTEXTWEAVE_MCP_API_KEY` 时功能正常；
  - 仅设置 `MCP_API_KEY` 时仍可兼容；
  - 两者都存在时优先使用新变量。

## 风险与回滚
- 风险：用户本地仍使用旧变量导致误判为不可用。
- 缓解：保留兼容读取并在错误信息中给出迁移指引。
- 回滚：若异常，可临时恢复“旧变量优先”读取顺序，待下一版再推进完全切换。
