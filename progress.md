
## 2026-06-23 - Task: 新增 Anthropic Messages API 格式支持

### What was done
新增 Anthropic (Claude) Messages API 兼容端点 /v1/messages，实现 Anthropic 格式 ↔ OpenAI 格式双向转换。新增 anthropic_compat.py 模块，修改 app.py、models.py、openai_compat.py、config.py，新增 53 个测试用例。

### Testing
- pytest tests/ 全部 120 个测试通过 (67 原有回归 + 53 新增)，零失败
- 覆盖范围：消息转换、工具调用双向映射、流式/非流式、SSE 编码、错误响应、鉴权校验、参数验证

### Notes
改动文件清单：
- reebuff2api/anthropic_compat.py (新增) — Anthropic 兼容层：消息规范化、上游 payload 构建、非流式累加器、流式状态机、SSE 编码、错误响应
- reebuff2api/app.py (修改) — 新增 /v1/messages 端点 + _check_anthropic_auth 鉴权 + 流式/非流式 handler
- reebuff2api/models.py (修改) — 新增 Anthropic 模型别名 (claude-sonnet-4-20250514 等 → Freebuff 模型)
- reebuff2api/openai_compat.py (修改) — _UPSTREAM_CHAT_KEYS 新增 	op_k；
ormalize_chat_messages 支持 system_prompt 参数实现 Buffy prompt 可配置/可禁用
- reebuff2api/config.py (修改) — 新增 system_prompt_override 字段 + FREEBUFF_SYSTEM_PROMPT_OVERRIDE 环境变量
- 	ests/test_anthropic_compat.py (新增) — 37 个单元测试：消息转换、工具映射、payload 构建、累加器、流状态机、SSE 编码、错误响应
- 	ests/test_app_messages.py (新增) — 16 个端点测试：鉴权、模型校验、参数验证、格式化兼容

回滚方式：从 D:\桌面\freebuff2api-main-backup-20260623-163621 恢复整个项目

## 2026-06-23 - Task: 后台管理完善 — 请求记录 + 多 API Key + 模型限制

### What was done
为 freebuff2api 后台管理新增三大能力：API 请求历史记录（时间/模型/耗时/Tokens）、多 API Key 管理（每个 Key 可独立设置名称、密钥、允许调用的模型）、Key 级模型限制（请求模型不在白名单则返回 403）。同时增强概览页显示实时请求统计。

### Testing
- tests/test_new_features.py：10 项全部通过
- 全模块 Python 编译检查通过
- app 初始化路由注册正常（38 条路由）

### Notes
改动文件：freebuff2api/usage.py (新增)、freebuff2api/usage_store.py (新增)、freebuff2api/config.py (修改)、freebuff2api/app.py (修改)、freebuff2api/admin.py (修改)、freebuff2api/admin_static/index.html (修改)、tests/test_new_features.py (新增)、data/ (新增)

回滚方式：git revert 本次 commit

## 2026-06-24 - Task: PR #3 代码审查与 Bug 修复

### What was done
拉取 main 最新合并 PR #3 (4 个 commit)，逐项审查 8 处改动，发现并修复 1 个 Bug：OpenAI /v1/chat/completions 端点 403 错误误返回 Anthropic 格式。更新 README 更新日志。

### Testing
- pytest tests/ 全部 120 个测试通过

### Notes
改动文件清单：
- freebuff2api/app.py (修改) — 修复 chat_completions 403 错误从 anthropic_error_payload 恢复为标准 OpenAI {"error": {...}} 格式
- README.md (修改) — 新增 2026-06-24 更新日志条目
- progress.md (修改) — 追加本轮任务记录

PR #3 合并内容（来自 qianze0628/main，4 commits）：
- anthropic_compat.py: reasoning_content 往返保留、SSE text block index 动态分配、空 content 守卫、model 名保留
- app.py: /v1/messages Anthropic 错误响应、requested_model 保留、/api/keep-warm 端点
- tests/test_app_messages.py: 错误响应断言适配 Anthropic format
- .vercel/: Vercel 项目配置文件（含 projectId/orgId，建议后续清理）

回滚方式：git revert cca2de3

## 2026-06-24 - Task: 移除 Anthropic 模型别名映射

### What was done
删除 models.py 中的 ANTHROPIC_MODEL_ALIASES 别名表和 _resolve_alias 函数，简化 resolve_model 逻辑。Anthropic /v1/messages 与 OpenAI /v1/chat/completions 统一只认原生模型 ID（deepseek/deepseek-v4-flash 等10个），传 Claude 风格名字直接返回 400。

### Testing
- pytest tests/ 全部 120 个测试通过（test_messages_endpoint_rejects_unknown_model 已同步更新为验证 400）
- 端到端 5 场景验证：短对话、9 轮多轮、20 轮长对话、system prompt、超长 prompt — 全部 200

### Notes
改动文件清单：
- freebuff2api/models.py (修改) — 删除 ANTHROPIC_MODEL_ALIASES 字典和 _resolve_alias 函数，去掉 resolve_model 中的别名分支
- tests/test_app_messages.py (修改) — test_messages_endpoint_accepts_anthropic_alias_model 重命名为 test_messages_endpoint_rejects_unknown_model，断言改为 assertEqual(400)

回滚方式：git revert 本次 commit
