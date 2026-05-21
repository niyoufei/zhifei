# ZDoc Preview-Only Route Same-Origin Proxy Code Implementation Stage Review

## 1. Scope

本文档归档 Step 195：preview-only route same-origin proxy code implementation 的阶段复核结果。

本步为 docs-only / stage-review-only：

- 不修改代码。
- 不修改 tests。
- 不修改 frontend。
- 不修改既有 docs。
- 不运行 pytest。
- 不启动服务。
- 不访问端口。
- 不运行 Ollama。
- 不调用 `/local-trial/preview-only`。
- 不触发 `/generate`。
- 不触发 `/export_docx`。
- 不触发 `/review/apply`。
- 不触发 ZBid 写回。
- 不生成 DOCX。
- 不写 `output/job/export`。
- 不进入真实 ZDoc/ZBid 联调。
- 不进入约 50 人团队正式部署设计。

## 2. Authorization Baseline

Step 195 的授权来源为 Step 194 推荐方案 A：

- 仅允许在前端服务层新增 `/local-trial/preview-only` 专用同源 proxy route。
- 仅允许将该路径转发至后端 preview-only route。
- 不允许新增通用 proxy。
- 不允许新增任意路径转发。
- 不允许暴露正式生成、DOCX 导出、review/apply 或 ZBid 写回入口。
- 不允许修改后端正式生成链、DOCX 导出链、review/apply 链或 ZBid 写回链。
- 不允许启动服务或执行 runtime smoke。

Step 195 的实际执行范围符合该授权：只完成前端服务层最小代码实现与静态验证。

## 3. Files Changed in Step 195

Step 195 实际修改文件：

- `frontend_web/app.py`

未修改：

- 后端代码。
- tests。
- 既有 docs。
- 前端模板与静态样式。
- 配置文件。
- 部署脚本。
- `output/job/export`。

## 4. Implementation Summary

Step 195 在 `frontend_web/app.py` 中新增了前端服务层专用同源 proxy：

- 新增 route：`POST /local-trial/preview-only`
- 转发目标：`${TDOCSYS_BACKEND_BASE_URL:-http://127.0.0.1:18760}/local-trial/preview-only`
- 请求体：JSON body 透传。
- 响应：后端响应 body / status / content-type 透传。
- 后端不可达时：返回明确的 preview-only / no-write 错误。
- JSON 非法时：返回明确的 preview-only / no-write 错误。

新增的错误响应保持安全边界：

- `preview_only=true`
- `no_write=true`
- `error=preview_only_route_proxy_failed`
- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`
- `calls_generate_route=false`
- `calls_export_docx_route=false`
- `calls_review_apply_route=false`
- `affects_zbid_writeback=false`
- `writes_output=false`
- `writes_job=false`
- `writes_export=false`

## 5. Boundary Confirmation

Step 195 已确认：

- 未引入通用 proxy。
- 未新增任意路径转发。
- 未暴露 `/generate`。
- 未暴露 `/export_docx`。
- 未暴露 `/review/apply`。
- 未暴露 ZBid 写回入口。
- 未新增 DOCX 生成入口。
- 未新增 `output/job/export` 写入路径。
- 未修改后端正式生成链。
- 未修改 DOCX 导出链。
- 未修改 review/apply。
- 未修改 ZBid 写回链。
- 未修改前端页面的 `fetch("/local-trial/preview-only")` 调用点。

该 proxy 仅面向本地 preview-only route 接入问题，不代表正式生成链、导出链、review/apply 或 ZBid 写回链开放。

## 6. Static Verification Completed

Step 195 已完成以下静态验证：

- `git diff --check`：通过。
- Python AST 静态解析：通过。
- 路由装饰器静态扫描：通过。

静态扫描确认新增路由位于前端服务层：

- route function：`local_trial_preview_only_proxy`
- route method：`POST`
- route path：`/local-trial/preview-only`

Step 195 未运行 pytest，符合用户禁止事项。

## 7. Not Verified Yet

Step 195 未验证以下运行时事项：

- 未启动后端服务。
- 未启动前端服务。
- 未访问任何本地端口。
- 未调用 `/local-trial/preview-only`。
- 未执行同源 proxy runtime smoke。
- 未验证前端端口 `18761` 上的 `POST /local-trial/preview-only` 是否能成功转发至后端。
- 未验证前端 `fetch("/local-trial/preview-only")` 是否能通过前端同源路径动态展示后端数据。
- 未验证后端不可达时的页面错误展示。

因此，Step 195 只能说明代码实现与静态验证通过，不能说明 runtime proxy 已通过。

## 8. Strict Non-Occurrence Confirmation

Step 195 严格未发生：

- 未运行 pytest。
- 未启动服务。
- 未访问端口。
- 未运行 Ollama。
- 未调用 `/local-trial/preview-only`。
- 未调用 `/generate`。
- 未调用 `/export_docx`。
- 未调用 `/review/apply`。
- 未触发 ZBid 写回。
- 未调用 ZBid API / DB / writeback。
- 未生成 DOCX。
- 未写 `output/job/export`。
- 未进入正式生成链。
- 未进入真实 ZDoc/ZBid 联调。
- 未进入约 50 人团队正式部署设计。

## 9. Risk Conclusion

当前风险结论：

1. Step 195 仅完成代码实现和静态验证，不代表 runtime proxy 已验证。
2. 前端 `fetch("/local-trial/preview-only")` 是否可经 `18761` 同源转发到后端仍需后续 controlled smoke。
3. 当前不代表进入正式生成链。
4. 当前不代表可生成 DOCX。
5. 当前不代表可执行 review/apply。
6. 当前不代表可写回 ZBid。
7. 当前不代表真实 ZDoc/ZBid 联调已完成。

## 10. Recommended Next Step

建议下一步为：

`ZDoc Step 197：preview-only route same-origin proxy controlled smoke authorization request`

建议性质：

- docs-only / authorization-request-only。
- 先起草受控 smoke 授权请求。
- 用户明确授权后，才可启动后端和前端服务。
- smoke 仍必须保持 preview-only / no-write。
- smoke 仅允许访问 `/local-trial/preview-only`、前端页面和必要健康检查。
- 不得触发 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回。
- 不得生成 DOCX。
- 不得写 `output/job/export`。
- 不得进入真实 ZDoc/ZBid 联调。
- 不得进入约 50 人团队正式部署设计。

## 11. Safety Conclusion

Step 195 完成了 `/local-trial/preview-only` 专用同源 proxy 的前端服务层代码实现。

当前系统状态：

- 代码层已具备前端同源 proxy route。
- 该 route 仅限 preview-only。
- 未引入通用 proxy。
- 未开放正式链入口。
- 未完成 runtime smoke。
- 未证明前端动态加载已成功。

后续必须在用户明确授权后，才可进入 Step 197 或后续 controlled smoke。
