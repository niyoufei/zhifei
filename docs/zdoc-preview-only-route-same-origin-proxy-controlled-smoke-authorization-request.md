# ZDoc Preview-Only Route Same-Origin Proxy Controlled Smoke Authorization Request

## 1. Purpose

本文档用于起草 Step 198：preview-only route same-origin proxy controlled smoke 的授权请求。

本步仅为 docs-only / authorization-request-only：

- 不代表用户已经授权。
- 不启动服务。
- 不访问端口。
- 不调用 `/local-trial/preview-only`。
- 不执行 runtime smoke。
- 不触发正式链。

只有用户后续明确授权后，才可进入 Step 198。

## 2. Current Baseline

当前已完成：

- Step 193 已发现同源 route / proxy 不成立：
  - 后端 `127.0.0.1:18760` 的 `POST /local-trial/preview-only` 返回 HTTP `200`。
  - 前端 `127.0.0.1:18761` 的 `POST /local-trial/preview-only` 返回 HTTP `404`。
  - 前端 `fetch("/local-trial/preview-only")` 无法动态加载后端 preview-only 数据。
- Step 194 已完成 same-origin proxy fix design，并推荐方案 A：前端服务层新增 preview-only 专用同源 proxy。
- Step 195 已按方案 A 完成代码实现：
  - 新增 `POST /local-trial/preview-only`。
  - 转发目标为 `${TDOCSYS_BACKEND_BASE_URL:-http://127.0.0.1:18760}/local-trial/preview-only`。
  - JSON body 透传。
  - 后端响应 body / status / content-type 透传。
  - 后端不可达或 JSON 非法时返回 preview-only / no-write 错误。
- Step 196 已完成 stage review，明确 Step 195 只完成代码实现与静态验证。

当前仍未验证：

- 未启动后端服务。
- 未启动前端服务。
- 未访问本地端口。
- 未调用 `/local-trial/preview-only`。
- 未执行同源 proxy runtime smoke。
- 前端端口 `18761` 上的 `POST /local-trial/preview-only` 是否可转发至后端仍未验证。
- 前端 `fetch("/local-trial/preview-only")` 是否能动态展示后端数据仍未验证。

## 3. Requested Smoke Purpose

拟申请 Step 198 controlled smoke 的目的：

1. 验证前端端口 `POST /local-trial/preview-only` 是否可通过同源 proxy 转发至后端。
2. 验证前端 `fetch("/local-trial/preview-only")` 是否由 Step 193 的 HTTP `404` 修复为可达。
3. 验证前端是否能动态展示：
   - `preview_packet`
   - `validator_result`
   - `blocked_reasons`
   - `generate_called=false`
   - `export_docx_called=false`
   - `review_apply_called=false`
   - `zbid_writeback_called=false`
   - `output_job_export_written=false`
4. 验证同源 proxy 仍保持 preview-only / no-write / no-formal-chain。
5. 验证 smoke 前后未写 `output/job/export`。
6. 验证本次启动的服务可以停止。

## 4. Requested Authorization Scope

拟申请用户授权的 Step 198 范围仅限：

1. 执行 Git preflight 只读检查：
   - `pwd`
   - `git branch --show-current`
   - `git rev-parse HEAD`
   - `git status --short`
   - `git tag --points-at HEAD`

2. 只读记录 `output/job/export` 前后快照：
   - smoke 前记录快照。
   - smoke 后记录快照。
   - 比对前后差异。
   - 不创建目录。
   - 不写入 `output/job/export`。

3. 启动后端服务：
   - 仅用于 `/local-trial/preview-only` preview-only route。
   - 可访问必要健康检查。
   - 不访问 `/generate`、`/export_docx`、`/review/apply`。
   - 检查结束后必须停止。

4. 启动前端服务：
   - 仅用于访问本地前端页面。
   - 仅用于验证同源 proxy。
   - 检查结束后必须停止。

5. 访问本地前端页面：
   - 仅用于确认 preview-only 面板可见。
   - 仅用于触发前端 `fetch("/local-trial/preview-only")`。
   - 不点击或提交正式生成、正式导出、review/apply 或 ZBid 写回入口。

6. 调用 `/local-trial/preview-only`：
   - 允许直接调用后端 `POST /local-trial/preview-only`。
   - 允许调用前端同源 `POST /local-trial/preview-only`。
   - 允许通过前端页面触发同源 `fetch("/local-trial/preview-only")`。
   - 只使用 fake/local trial metadata。
   - 不读取真实正文。
   - 不生成真实 candidate patch。
   - 不执行真实 ZDoc/ZBid 联调。

7. 生成 Step 198 smoke report：
   - 仅生成回报文本或后续授权指定的 docs report。
   - 不生成 DOCX。
   - 不写 `output/job/export`。

8. 停止本次启动的服务：
   - 只停止本次记录的后端 PID。
   - 只停止本次记录的前端 PID。
   - 确认对应端口无监听。
   - 不使用破坏性批量 kill。

## 5. Explicitly Not Authorized

Step 198 授权请求不包括：

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid 写回
- ZBid API / DB / writeback
- DOCX 文件生成
- JSON / Markdown 正式导出
- `output/job/export` 写入
- formal writeback
- formal writeback dry-run
- 修改 source section
- 真实 candidate patch 写入
- 真实 ZDoc/ZBid 联调
- 运行 Ollama
- 运行 `ollama serve`
- 访问 `127.0.0.1:11434`
- 下载或拉取模型
- 调用模型生成正文
- 约 50 人团队正式部署设计
- Mac Studio / NAS / UPS / Redis / PostgreSQL 正式部署配置

## 6. Smoke Checks To Perform If Authorized

如果用户授权 Step 198，建议 controlled smoke 至少检查：

1. Git preflight 通过。
2. `git status --short` smoke 前为空。
3. `output/job/export` 前置快照为空或无新增。
4. 后端服务可启动。
5. 前端服务可启动。
6. `GET /index` 返回 HTTP `200`。
7. 后端 `POST /local-trial/preview-only` 返回 HTTP `200`。
8. 前端同源 `POST /local-trial/preview-only` 返回 HTTP `200`。
9. Step 193 的前端同源 HTTP `404` 已修复。
10. 前端页面能够通过 `fetch("/local-trial/preview-only")` 动态展示 `preview_packet`。
11. 前端页面能够动态展示 `validator_result`。
12. 前端页面能够动态展示 `blocked_reasons`。
13. 前端页面能够动态展示：
    - `generate_called=false`
    - `export_docx_called=false`
    - `review_apply_called=false`
    - `zbid_writeback_called=false`
    - `output_job_export_written=false`
14. 后端响应仍为 `preview_only=true`。
15. 后端响应仍为 `no_write=true`。
16. 正式链 flags 均为 false。
17. `output/job/export` 后置快照无新增。
18. 本次启动的服务均已停止。

## 7. Hard Stop Conditions

Step 198 如获授权，执行中出现任一情况必须立即停止并回报：

- 当前目录错误。
- 分支错误。
- HEAD 不一致。
- `git status --short` 非空。
- 未授权动作出现。
- 后端启动失败且无可读错误。
- 前端启动失败且无可读错误。
- 前端同源 proxy 仍返回非预期结果。
- 任一正式链 flag 为 true。
- 出现 `output/job/export` 写入。
- 出现 DOCX 文件。
- 触发 `/generate`。
- 触发 `/export_docx`。
- 触发 `/review/apply`。
- 触发 ZBid 写回。
- 调用 ZBid API / DB / writeback。
- 运行 Ollama 或访问 `127.0.0.1:11434`。
- 服务无法停止。
- 页面仍无法展示 preview-only 数据。
- 页面把 advisory 显示为 evidence。
- 页面把 preview 显示为正式正文。

## 8. Required Runtime Report Template

Step 198 如获授权，完成后应回报：

- 用户授权范围。
- 实际执行命令。
- 当前目录。
- 当前分支。
- 开始前 HEAD。
- 结束后 HEAD。
- `git status --short` 前后结果。
- 后端启动命令。
- 后端 PID。
- 后端停止状态。
- 前端启动命令。
- 前端 PID。
- 前端停止状态。
- 访问的本地端口。
- 调用的接口。
- 后端 `POST /local-trial/preview-only` 结果。
- 前端同源 `POST /local-trial/preview-only` 结果。
- 前端 `fetch("/local-trial/preview-only")` 展示结果。
- `preview_packet` 是否可见。
- `validator_result` 是否可见。
- `blocked_reasons` 是否可见。
- 五个正式链 false flags 是否可见。
- 同源 proxy 是否成立。
- 是否运行 Ollama。
- 是否触发 `/generate`。
- 是否触发 `/export_docx`。
- 是否触发 `/review/apply`。
- 是否触发 ZBid 写回。
- 是否生成 DOCX。
- 是否写 `output/job/export`。
- `output/job/export` 前后快照是否有差异。
- 是否存在 high risk。
- 是否存在未停止进程。
- 风险说明。
- 下一步建议。

## 9. User Confirmation Wording

Step 198 必须等待用户明确回复授权。建议用户授权确认语为：

```text
我授权执行 Step 198 preview-only route same-origin proxy controlled smoke，授权范围仅限 Step 197 授权请求文档列明事项；允许启动后端和前端、访问本地页面并调用 /local-trial/preview-only；不得触发 /generate、/export_docx、/review/apply、ZBid 写回，不得生成 DOCX，不得写 output/job/export，不得运行 Ollama，不得进入真实 ZDoc/ZBid 联调，不得进入 50 人正式部署设计。
```

未收到上述或等效明确授权，不得进入 Step 198。

## 10. Next Step Recommendation

建议下一步为：

`ZDoc Step 198：preview-only route same-origin proxy controlled smoke execution`

Step 198 必须在用户明确授权后才可执行。

如用户未授权，应停止，不得启动服务、访问端口或调用 `/local-trial/preview-only`。

## 11. Safety Conclusion

本文档仅完成 Step 198 controlled smoke 授权请求草案。

当前仍未执行 runtime smoke：

- 未启动后端。
- 未启动前端。
- 未访问端口。
- 未调用 `/local-trial/preview-only`。
- 未验证同源 proxy runtime。
- 未进入真实 ZDoc/ZBid 联调。
- 未进入约 50 人团队正式部署设计。

本授权请求文档不代表用户已经授权。
