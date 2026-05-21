# ZBid Preview-Only Receiver Repository Readiness Verification Authorization Request

## 1. Purpose

本文档对应 Step 205：ZBid preview-only receiver repository readiness verification authorization request。

本步仅起草 ZBid 候选仓库只读核验授权请求，用于后续向用户申请明确授权。本文档只代表申请授权，不代表用户已经授权。

本步性质为 docs-only / authorization-request-only / no-zbid-access / no-code-change / no-service / no-port-access / no-writeback：

- 不修改代码。
- 不修改 tests。
- 不修改 frontend。
- 不修改既有 docs。
- 不访问 ZBid 仓库。
- 不运行 pytest。
- 不启动服务。
- 不访问端口。
- 不运行 Ollama。
- 不调用 `/local-trial/preview-only`。
- 不调用任何 ZBid endpoint。
- 不触发 `/generate`。
- 不触发 `/export_docx`。
- 不触发 `/review/apply`。
- 不触发 ZBid 写回。
- 不生成 DOCX。
- 不写 `output/job/export`。
- 不进入真实 ZDoc/ZBid 联调。
- 不进入 50 人正式部署设计。

本文档不得被视为 Step 206 的执行授权，也不得被视为 ZBid receiver 代码实现授权。

## 2. Authorization Request Source

本授权请求基于 Step 204：ZBid preview-only receiver repository boundary confirmation design。

Step 204 已标注的候选信息为：

- 当前候选 ZBid 仓库路径：`/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- 当前候选分支：`local-llm-integration-clean`

重要边界：

- 以上仍为候选信息。
- Step 204 未访问该候选仓库。
- Step 205 也不访问该候选仓库。
- 未获得用户明确授权前，不得访问或修改该候选 ZBid 仓库。
- 未获得用户明确授权前，不得核验该候选仓库路径、分支、HEAD 或工作区状态。

## 3. Requested Read-Only Verification Scope for Step 206

后续拟申请 Step 206 执行以下只读核验：

- 只读进入候选 ZBid 仓库。
- 查看当前目录。
- 查看当前分支。
- 查看 HEAD。
- 查看 `git status --short`。
- 只读查看仓库结构。
- 只读查找 preview-only 相关候选文件。
- 只读查找 mock 相关候选文件。
- 只读查找 local-llm 相关候选文件。
- 只读查找 ZBid 接收相关候选文件。
- 只读查找正式写回、导出、review/apply 等禁止链路的边界位置。
- 不修改任何文件。
- 不启动服务。
- 不访问端口。
- 不调用任何 endpoint。
- 不运行任何业务流程。

Step 206 如获得授权，也只能是 repository readiness verification / read-only，不是 ZBid receiver 代码实现。

## 4. Read-Only Verification Goals

Step 206 的只读核验目标应限定为：

1. 确认候选 ZBid 仓库路径是否存在。
2. 确认候选仓库是否为 git 仓库。
3. 确认当前分支是否为 `local-llm-integration-clean`。
4. 确认开始前 HEAD。
5. 确认 `git status --short` 是否为空。
6. 只读了解仓库结构。
7. 只读定位 preview-only / mock / local-llm / ZBid receiver 相关候选文件。
8. 只读确认后续可能允许修改的候选文件范围。
9. 只读确认后续必须禁止修改的正式链文件范围。
10. 只读确认禁止写回边界。

Step 206 不应产生代码修改、测试修改、文档修改、运行时文件、数据库写入、模型调用或服务进程。

## 5. Required Confirmation Before Any Future ZBid Code Change

真正进入 ZBid 代码修改前，还必须另行取得用户对以下内容的明确授权：

- ZBid 仓库路径。
- ZBid 分支。
- ZBid 开始前 HEAD。
- ZBid clean 状态。
- 允许新增文件范围。
- 允许修改文件范围。
- 禁止修改文件范围。
- 是否允许新增 tests。
- 是否允许运行 tests。
- 是否允许启动服务。
- 是否允许访问端口。
- 是否允许调用 ZBid preview-only receiver。
- 是否允许跨系统 ZDoc -> ZBid preview-only 调用。
- 禁止写回边界。
- 禁止生成 DOCX。
- 禁止写 `output/job/export`。

如果上述任一项未明确，不得修改 ZBid 代码。

## 6. Explicitly Not Authorized in Step 206

即使用户授权 Step 206，只读核验也不授权：

- 不授权修改 ZBid 代码。
- 不授权修改 ZDoc 代码。
- 不授权修改 tests。
- 不授权修改 docs。
- 不授权启动 ZBid 服务。
- 不授权启动 ZDoc 服务。
- 不授权访问本地端口。
- 不授权调用 `/local-trial/preview-only`。
- 不授权调用任何 ZBid endpoint。
- 不授权执行 ZDoc/ZBid 跨系统调用。
- 不授权运行 pytest。
- 不授权运行 Ollama。
- 不授权触发 `/generate`。
- 不授权触发 `/export_docx`。
- 不授权触发 `/review/apply`。
- 不授权触发 ZBid 写回。
- 不授权生成 DOCX。
- 不授权写 `output/job/export`。
- 不授权进入真实 ZDoc/ZBid 联调。
- 不授权进入 50 人正式部署设计。

## 7. Forbidden Chains

Step 206 以及后续 ZBid receiver 相关阶段必须保持以下禁止链路：

- 不得触发 `/generate`。
- 不得触发 `/export_docx`。
- 不得触发 `/review/apply`。
- 不得触发 ZBid 写回。
- 不得调用 ZBid 正式写回 API。
- 不得访问 ZBid 正式业务数据库做写入。
- 不得写回 ZDoc。
- 不得写回 ZBid 正式业务数据。
- 不得生成 DOCX。
- 不得生成正式 JSON / Markdown / job / export 产物。
- 不得写 `output/job/export`。
- 不得进入正式正文生成链。
- 不得生成真实 candidate patch。
- 不得执行 formal writeback。
- 不得执行 formal writeback dry-run。
- 不得进入 50 人正式部署设计。

任何错误处理不得 fallback 到正式接口或写回链。

## 8. Proposed Read-Only Commands for Step 206

如用户后续授权 Step 206，可申请只读执行类似命令：

```bash
pwd
git branch --show-current
git rev-parse HEAD
git status --short
find . -maxdepth 2 -type f | sort | sed -n '1,200p'
rg -n "preview-only|preview_only|local-llm|local_llm|mock|ZBid|zbid|writeback|export_docx|review/apply|generate" .
```

上述命令仅为后续授权后的候选只读命令清单，不代表本步允许执行。

如授权执行 Step 206，命令清单应在执行前再次由用户确认；如任一命令可能启动服务、访问端口、修改文件或触发业务接口，应跳过并回报。

## 9. Stop Conditions for Step 206

如后续执行 Step 206，只读核验中出现以下情况应立即停止：

- 当前目录不是授权的 ZBid 候选路径。
- 分支不是用户授权分支。
- HEAD 与用户授权 HEAD 不一致。
- `git status --short` 非空。
- 命令需要写文件。
- 命令可能启动服务。
- 命令可能访问端口。
- 命令可能调用 endpoint。
- 出现未授权文件修改。
- 出现运行时文件写入。
- 出现 output/job/export 写入。
- 出现 DOCX 文件生成。
- 发现需要进入代码实现才能继续。

停止后只回报只读核验结果和风险，不得自行修复。

## 10. Proposed User Authorization Wording

用户如同意进入 Step 206，可明确回复类似以下授权语：

> 我授权执行 Step 206：ZBid preview-only receiver repository readiness verification，授权范围仅限 Step 205 授权请求文档列明事项；允许只读进入候选 ZBid 仓库 `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`，只读核验当前目录、分支、HEAD、`git status --short`、仓库结构和 preview-only / mock / local-llm / ZBid receiver 相关候选文件；不得修改任何文件，不得启动服务，不得访问端口，不得调用任何 ZBid endpoint，不得触发 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回，不得生成 DOCX，不得写 `output/job/export`，不得进入真实 ZDoc/ZBid 联调，不得进入 50 人正式部署设计。

必须说明：

- 未收到上述或等效明确授权，不得执行 Step 206。
- Step 206 只能是 read-only repository readiness verification。
- Step 206 不是 ZBid receiver 代码实现。
- Step 206 不授权修改 ZBid 代码。
- Step 206 不授权启动服务、访问端口或调用接口。

## 11. Step 206 Report Template Recommendation

如后续 Step 206 获得授权，完成后至少应回报：

- 授权范围。
- 当前目录。
- 当前分支。
- 开始前 HEAD。
- `git status --short`。
- 候选路径是否存在。
- 是否为 git 仓库。
- 仓库结构只读摘要。
- preview-only 相关候选文件。
- mock 相关候选文件。
- local-llm 相关候选文件。
- ZBid receiver 相关候选文件。
- 后续可能允许修改的候选文件范围。
- 后续必须禁止修改的正式链文件范围。
- 是否修改任何文件。
- 是否启动服务。
- 是否访问端口。
- 是否调用 endpoint。
- 是否触发 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回。
- 是否生成 DOCX。
- 是否写 `output/job/export`。
- 风险说明。
- 下一步建议。

## 12. Next Step Recommendation

建议下一步为：

`ZDoc Step 206：ZBid preview-only receiver repository readiness verification`

前提：

- 必须用户明确授权。
- 授权必须限定 read-only / no-code-change / no-service / no-port-access / no-writeback。
- 授权必须明确候选 ZBid 仓库路径。
- 授权必须明确候选分支。
- 授权必须明确不得修改任何文件。

Step 206 完成后，如需要进入 ZBid receiver 代码实现，仍必须再起草或取得新的明确授权。

## 13. Safety Conclusion

Step 205 仅完成 ZBid 候选仓库只读核验授权请求文档。

本步不代表：

- 已授权访问 ZBid 仓库。
- 已访问 ZBid 仓库。
- 已核验 ZBid 分支或 HEAD。
- 已授权修改 ZBid 代码。
- 已实现 ZBid receiver。
- 已启动服务。
- 已访问端口。
- 已调用任何 endpoint。
- 已进入真实 ZDoc/ZBid 联调。
- 已触发正式生成、DOCX 导出、review/apply 或 ZBid 写回。
- 已写 `output/job/export`。
- 已进入 50 人正式部署设计。

后续任何 ZBid 仓库访问、代码修改、服务启动、端口访问、接口调用、ZBid 侧接收验证或跨系统联调，均需单独明确授权。
