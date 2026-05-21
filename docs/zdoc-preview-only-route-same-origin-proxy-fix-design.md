# ZDoc Preview-Only Route Same-Origin Proxy Fix Design

## 1. Scope

本文档对应 Step 194：`/local-trial/preview-only` 前端同源 route / proxy 修复方案设计。

本步仅为 docs-only / design-only：

- 不修改代码。
- 不修改 tests。
- 不修改 frontend。
- 不修改既有 docs。
- 不运行 pytest。
- 不启动服务。
- 不访问端口。
- 不运行 Ollama。
- 不调用 `/local-trial/preview-only`。
- 不触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回。
- 不生成 DOCX。
- 不写 `output/job/export`。
- 不进入真实 ZDoc/ZBid 联调。
- 不进入约 50 人团队正式部署设计。

本文档不代表已经授权代码修改。后续任何代码实现必须在用户明确授权后单独执行。

## 2. Step 193 Finding

Step 193 controlled smoke 已确认：

- 后端 `127.0.0.1:18760` 的 `POST /local-trial/preview-only` 返回 HTTP `200`。
- 前端 `127.0.0.1:18761` 的 `POST /local-trial/preview-only` 返回 HTTP `404`。
- 前端页面中的 `fetch("/local-trial/preview-only")` 当前无法动态加载后端 preview-only 数据。
- 前端页面静态展示面板已经存在，可显示 `preview_packet`、`validator_result`、`blocked_reasons` 和五个正式链 false flags 的展示区域。
- 后端 route 自身已返回 `preview_only=true`、`no_write=true`、`blocked_reasons` 和正式链 false flags。

Step 193 同时确认：

- 未触发 `/generate`。
- 未触发 `/export_docx`。
- 未触发 `/review/apply`。
- 未触发 ZBid 写回。
- 未写 `output/job/export`。
- 后端和前端服务均已停止。

## 3. Root Cause

当前前端与后端在本地 smoke 中分属不同端口：

- 后端 FastAPI：`http://127.0.0.1:18760`
- 前端 Flask：`http://127.0.0.1:18761`

前端代码使用相对路径：

```javascript
fetch("/local-trial/preview-only")
```

浏览器会把该请求发送到当前页面所在 origin，即：

```text
http://127.0.0.1:18761/local-trial/preview-only
```

但当前前端 Flask 服务未提供 `/local-trial/preview-only` 同源转发 route / proxy，因此请求没有被转发到后端 `18760`，最终返回 HTTP `404`。

根因判断：

1. 前端和后端运行在不同端口。
2. 前端服务未提供同源转发 route / proxy。
3. 当前相对路径请求落在前端端口 `18761`，未转发到后端端口 `18760`。
4. 后端 route 本身可用，问题集中在前端到后端的同源接入层。

## 4. Fix Goals

后续修复目标：

1. 保持 `fetch("/local-trial/preview-only")` 不变，或尽量减少前端 JS 变更。
2. 通过前端同源代理或统一入口，使前端同源路径能够转发到后端 preview-only route。
3. 仅允许转发 `/local-trial/preview-only`。
4. 保持 preview-only / no-write / no-formal-chain 边界。
5. 不引入 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回等正式链入口。
6. 不写 `output/job/export`。
7. 不调用 Ollama。
8. 不调用模型。
9. 不把 advisory 当作 evidence。
10. 不把 preview 当作正式正文。

## 5. Option A: Frontend Same-Origin Proxy Route

方案 A：在前端 Flask 服务层新增一个最小同源 proxy route：

```text
POST /local-trial/preview-only
```

该 route 只转发到后端：

```text
POST http://127.0.0.1:<backend_port>/local-trial/preview-only
```

设计边界：

- 只允许 `POST /local-trial/preview-only`。
- 不新增 `/generate` proxy。
- 不新增 `/export_docx` proxy。
- 不新增 `/review/apply` proxy。
- 不新增 ZBid 写回 proxy。
- 不新增通配 proxy。
- 不允许把任意 path 透传到后端。
- 不写文件。
- 不创建 DOCX。
- 不访问 `output/job/export`。
- 不调用模型。
- 不调用 Ollama。

建议实现形态：

- 在前端服务中读取一个本地后端 base URL 配置，例如 `TDOCSYS_BACKEND_BASE_URL`。
- 默认仅用于本地试用，例如 `http://127.0.0.1:18760`。
- route 收到请求后只把 JSON body 转发到后端 preview-only route。
- route 返回后端 JSON 和状态码。
- 如果后端不可达，只返回错误 JSON，不 fallback 到正式接口。
- 错误响应应保持 no-write 语义，例如 `preview_only_route_proxy_failed`。

优点：

- 前端现有 `fetch("/local-trial/preview-only")` 可以保持不变。
- 浏览器侧保持同源，避免 CORS 复杂度。
- 改动面集中在前端服务层。
- 可用 Step 193 同类 smoke 直接验证。
- 可以硬编码 allowlist，避免正式链暴露面扩大。

风险：

- 前端服务会引入一个后端调用能力，需要严格限定到 preview-only route。
- 必须避免通用代理实现。
- 必须避免读取或打印敏感配置。
- 必须确保失败时不 fallback 到 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回。

## 6. Option B: Configured Backend Base URL in Frontend JavaScript

方案 B：前端 JS 不再使用相对路径，而是使用配置化 backend base URL 直连后端：

```javascript
fetch(`${backendBaseUrl}/local-trial/preview-only`)
```

设计边界：

- backend base URL 必须明确配置。
- 仅允许调用 `/local-trial/preview-only`。
- 不允许调用 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回。
- 前端失败时只显示错误，不 fallback 到正式接口。

优点：

- 后端不需要通过前端服务转发。
- 请求路径更直接，便于区分后端服务地址。
- 可用于本地双端口 smoke。

风险：

- 浏览器跨 origin 请求需要 CORS 支持。
- 部署环境中 backend base URL 的来源、暴露方式和切换规则需要额外设计。
- 用户可能在页面源码或网络请求中看到后端地址。
- 如果配置错误，前端可能访问错误后端。
- 相比方案 A，会扩大浏览器侧网络边界，后续 smoke 需要覆盖 CORS 和环境配置。

## 7. Option C: Unified App or Reverse Proxy in Later Deployment

方案 C：后续部署阶段由同一应用入口或反向代理统一承载前后端，例如：

```text
/index
/static/*
/local-trial/preview-only
```

设计边界：

- 仅作为后续部署阶段方案。
- 当前本地小范围试用阶段不直接进入正式部署设计。
- 不进入 Mac Studio / NAS / UPS / Redis / PostgreSQL / 50 人并发设计。
- 不开放正式生成、DOCX 导出、review/apply 或 ZBid 写回入口。

优点：

- 长期路径更接近真实使用形态。
- 可以统一 TLS、cookie、日志、路由和访问控制。
- 前端相对路径天然成立。

风险：

- 超出当前本地 trial 最小修复范围。
- 需要部署设计和反向代理配置设计。
- 容易提前进入正式部署讨论，不适合作为 Step 195 的直接修复方案。

## 8. Recommended Option

推荐方案：方案 A，前端服务层新增 preview-only 专用同源 proxy route。

推荐理由：

1. 最小代码改动。
2. 可保持前端 `fetch("/local-trial/preview-only")` 不变。
3. 浏览器仍使用同源路径。
4. 不需要引入 CORS 新复杂度。
5. 可以把代理能力硬限定为 `/local-trial/preview-only`。
6. 不扩大正式链暴露面。
7. 后续 smoke 可直接验证：
   - `POST http://127.0.0.1:18761/local-trial/preview-only` 应返回 HTTP `200`。
   - 前端页面点击 preview-only 加载按钮后能展示 `preview_packet`、`validator_result`、`blocked_reasons` 和五个 false flags。
   - 不触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回。
   - 不写 `output/job/export`。

方案 A 的实现必须保持专用、窄口、no-write：

- 只实现 `POST /local-trial/preview-only`。
- 只转发到后端同名 preview-only route。
- 不实现通用 proxy。
- 不转发任意 URL。
- 不新增正式链 endpoint。
- 不修改后端正式生成链。
- 不修改 DOCX 导出链。
- 不修改 review/apply 链。
- 不修改 ZBid 写回链。

## 9. Step 195 Authorization Requirement

后续 Step 195 如进入代码实现，必须用户单独明确授权。

建议 Step 195 授权范围仅限：

- 修改前端服务层最小必要文件。
- 新增 `POST /local-trial/preview-only` 同源 proxy route。
- 仅允许转发到后端 `/local-trial/preview-only`。
- 可读取本地后端 base URL 配置，但不得打印敏感配置。
- 可新增最小前端/后端边界测试，如确有必要。
- 不修改后端正式生成链。
- 不修改 DOCX 导出链。
- 不修改 review/apply 链。
- 不修改 ZBid 写回链。
- 不修改 output/job/export。
- 不启动服务，除非用户在后续 smoke 步骤另行授权。

Step 195 不应授权：

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid 写回
- ZBid API / DB / writeback
- DOCX 生成
- output/job/export 写入
- Ollama
- 模型调用
- 真实 ZDoc/ZBid 联调
- 约 50 人团队正式部署设计

## 10. Future Smoke Acceptance Criteria

代码实现后，后续受控 smoke 应至少验证：

1. `GET /index` 返回 HTTP `200`。
2. 前端 origin 的 `POST /local-trial/preview-only` 返回 HTTP `200`。
3. 后端 origin 的 `POST /local-trial/preview-only` 仍返回 HTTP `200`。
4. 前端页面可以动态展示 `preview_packet`。
5. 前端页面可以动态展示 `validator_result`。
6. 前端页面可以动态展示 `blocked_reasons`。
7. 前端页面显示：
   - `generate_called=false`
   - `export_docx_called=false`
   - `review_apply_called=false`
   - `zbid_writeback_called=false`
   - `output_job_export_written=false`
8. 不触发 `/generate`。
9. 不触发 `/export_docx`。
10. 不触发 `/review/apply`。
11. 不触发 ZBid 写回。
12. 不生成 DOCX。
13. 不写 `output/job/export`。
14. 服务结束后无本步启动进程残留。

## 11. Safety Conclusion

Step 194 仅完成 `/local-trial/preview-only` 前端同源 route / proxy 修复方案设计。

当前结论：

- 后端 preview-only route 已可用。
- 前端静态展示面板已存在。
- 当前双端口运行方式下，同源 `fetch("/local-trial/preview-only")` 仍不成立。
- 推荐通过前端服务层新增 preview-only 专用同源 proxy route 修复。
- 本设计不代表已授权代码修改。
- 本设计不代表已经完成前后端真实联通。
- 本设计不代表正式生成、DOCX 导出、review/apply 或 ZBid 写回已开放。
