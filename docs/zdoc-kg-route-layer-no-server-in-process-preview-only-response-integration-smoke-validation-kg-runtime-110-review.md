# KG-RUNTIME-110 route-layer no-server in-process preview-only response integration smoke validation review

## 结论

KG-RUNTIME-110 smoke 结论：NO-GO。

本阶段未进入 ZDoc 接入、真实使用、试用阶段，也未进入 KG-RUNTIME-111。

## 基线

- 仓库：`/Users/youfeini/Desktop/文档生成系统`
- 分支：`main`
- 开始前 HEAD：`4aa153887992c22a09e62b57f2ffeb82ff29c22f`
- 开始前远端基线 tag：`v0.1.492-zdoc-kg-preview-only-response-smoke-pass-route-gate`
- `git status --short`：clean
- `git branch --show-current`：`main`
- `git rev-parse HEAD`：`4aa153887992c22a09e62b57f2ffeb82ff29c22f`
- `git ls-remote --tags origin v0.1.492-zdoc-kg-preview-only-response-smoke-pass-route-gate`：被 sandbox SSH 限制拒绝，未请求完全访问权限
- `git push --dry-run origin HEAD:refs/tags/v0.1.492-zdoc-kg-preview-only-response-smoke-pass-route-gate`：`Everything up-to-date`

## 实际执行

只执行了一次 no-server in-process Python smoke 调用。

调用方式：

- 直接导入 `backend.app.routers.kg_read_only_preview`
- 设置 `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED=1`
- 直接调用 `kg_read_only_preview_route(...)`
- 将 route 模块中的 `build_kg_read_only_preview` 替换为 synthetic adapter stub
- synthetic adapter 返回 content-safe `preview_only_response`
- 在实际 route 调用期间设置 guard，阻断真实 KG 目标正文读取、JSON parse、socket 创建和 TCP 连接

输入形态：

- 使用 synthetic / content-safe response 形态
- 未读取真实 KG 文件正文内容
- 未解析真实 KG JSON
- 未启动 uvicorn
- 未绑定 TCP 端口
- 未访问 `127.0.0.1`
- 未调用 `/kg/read-only-preview`
- 未调用 `/health`
- 未调用 `/generate`
- 未调用 `/export_docx`
- 未调用 `/review/apply`

Python smoke 输出：

```text
Traceback (most recent call last):
  File "<stdin>", line 279, in <module>
AssertionError
```

由于 smoke 在验证断言阶段失败，未返回 PASS 摘要。本阶段按 NO-GO 归档，不现场修改代码，不改用 uvicorn / TCP / endpoint / pytest / 真实 KG。

## 验证边界

已确认事项：

- 未启动 uvicorn
- 未绑定 TCP 端口
- 未访问 `127.0.0.1`
- 未调用真实 endpoint
- 未读取真实 KG 文件正文内容
- 未解析真实 KG JSON
- 使用 no-server in-process direct route 调用
- 使用 synthetic / content-safe response 形态
- 未接入 `/generate`
- 未接入 `/export_docx`
- 未接入 `/review/apply`
- 未写 output / job / export
- 未触发 ZBid 写回
- 未接入 RAG / registry / CI
- 未作为 evidence
- 未作为 scoring
- 未运行 Ollama
- 未修改 frontend / tests / config / JSON
- 未修改 adapter / route / helper / `main.py`
- 未执行目录扫描命令

未确认通过事项：

- 未确认 route 层正确透传 `preview_only_response`
- 未确认返回结构包含 `preview_contract` / `preview_only_mapping` / `audit_only_mapping` / `prohibited_mapping`
- 未确认 `preview_only_mapping` 仅包含允许字段
- 未确认 `audit_only_mapping` 仅包含允许字段
- 未确认 `prohibited_mapping` 仅保留禁止类别清单
- 未确认 `prohibited_mapping` 未进入 `preview_only_mapping`
- 未确认 `preview_only_mapping` 未包含 KG value / 正文 / evidence / scoring

## NO-GO 原因

唯一一次 no-server in-process direct route smoke 在断言阶段失败，输出为 `AssertionError`，未产生 PASS 结果。

按本阶段约束，smoke 不通过时不得现场修改代码、不得改用服务或端口、不得改用 pytest、不得读取真实 KG。本 review 文件仅归档 NO-GO 事实，等待下一阶段单独授权。

## 停止线

- 本阶段没有进入 ZDoc 接入阶段
- 本阶段没有进入真实使用阶段
- 本阶段没有进入试用阶段
- 本阶段没有进入 KG-RUNTIME-111
