# ZDoc-ZBid 20-user environment preflight review and startup readiness decision request

## 1. Step 266 只读环境 preflight 结果复盘

Step 266 已完成 20 人受控常态试运行启动前的只读环境 preflight 检查。

Step 266 的检查范围包括：

- ZDoc 仓库路径、分支、HEAD、`git status --short`。
- ZBid 仓库路径、分支、HEAD、`git status --short`。
- `127.0.0.1:18766` 与 `127.0.0.1:18767` 的监听状态。
- 疑似 ZDoc / ZBid 残留服务进程。
- Ollama 相关运行进程。
- 两仓 `output/job/export` 路径。
- DOCX 新增迹象。
- 日志、问题清单、回退记录目录状态。
- 与 Step 264 管理员 SOP、Step 265 preflight 清单的一致性。

Step 266 未启动 ZDoc 服务，未启动 ZBid 服务，未运行 Ollama，未向端口发起 HTTP 请求，未调用 endpoint，未触发 `/generate`、`/export_docx`、`/review/apply`，未触发 ZBid 写回，未生成 DOCX，未写 `output/job/export`。

## 2. ZDoc 仓库检查结论

Step 266 记录的 ZDoc 检查结果：

| 检查项 | 结果 | 结论 |
| --- | --- | --- |
| 仓库路径 | `/Users/youfeini/Desktop/文档生成系统` 存在 | 通过 |
| 分支 | `main` | 通过 |
| HEAD | `01820af738fe5abd513b9deb4687dca801a7ae86` | 通过 |
| `git status --short` | 空 | clean |

结论：ZDoc 仓库路径、分支、HEAD 与 Step 266 授权一致，工作区 clean。

## 3. ZBid 仓库检查结论

Step 266 记录的 ZBid 检查结果：

| 检查项 | 结果 | 结论 |
| --- | --- | --- |
| 仓库路径 | `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean` 存在 | 通过 |
| 分支 | `local-llm-integration-clean` | 通过 |
| HEAD | `378355755372e03ac4f4064af59b287054984c25` | 通过 |
| `git status --short` | 空 | clean |

结论：ZBid 仓库路径、分支、HEAD 与 Step 266 授权一致，工作区 clean。Step 266 未在 ZBid 仓库 commit、tag、push。

## 4. 端口 18766 / 18767 无监听结论

Step 266 使用只读监听检查方式确认：

| 端口 | Step 266 检查结果 | 结论 |
| --- | --- | --- |
| `127.0.0.1:18766` | 无监听输出 | 未被占用 |
| `127.0.0.1:18767` | 无监听输出 | 未被占用 |

结论：Step 266 时点建议端口均无监听。该结论只代表 Step 266 检查时点，不代表未来启动前无需再次检查。

## 5. 残留服务进程检查结论

Step 266 只读检查未发现疑似 ZDoc / ZBid 残留服务进程。

检查关注项包括：

- `uvicorn`
- `app.main:app`
- 当前 ZDoc 仓库路径相关命令
- ZBid clean 仓库路径相关命令

结论：Step 266 时点未发现疑似 ZDoc / ZBid 残留服务。

## 6. Ollama 进程检查结论

Step 266 只读检查未发现 Ollama 相关运行进程。

结论：Step 266 未运行 Ollama，也未发现当前正在运行的 Ollama 相关进程。

## 7. output/job/export 禁止路径检查结论

Step 266 记录：

| 仓库 | 检查路径 | 结果 | 结论 |
| --- | --- | --- | --- |
| ZDoc | `output/job/export` | `MISSING` | 未发现该路径 |
| ZBid | `output/job/export` | `MISSING` | 未发现该路径 |

结论：Step 266 未发现两仓存在 `output/job/export` 路径，也未写入该路径。

## 8. DOCX 生成迹象检查结论

Step 266 结论：

- ZDoc 仓库存在历史 `.docx` 文件。
- ZBid 仓库本次未列出 `.docx` 文件。
- ZDoc / ZBid 针对 `.docx`、`output`、`job`、`export`、`build`、`exports` 等路径的 `git status --short` 检查无输出。
- Step 266 未运行服务、未调用 endpoint、未生成 DOCX。

结论：历史 DOCX 文件不等于本轮新增 DOCX。Step 266 未发现新增 DOCX 文件迹象。

## 9. AI知识图谱大全 文件夹未访问声明

用户已暂停 `/Users/youfeini/Desktop/AI知识图谱大全` 文件夹识别任务。

Step 266 未访问、扫描、读取、复制、移动、分析或识别该文件夹。

本 Step 267 同样未访问、扫描、读取、复制、移动、分析或识别该文件夹。

## 10. 与 Step 264 管理员 SOP 的一致性结论

Step 264 管理员 SOP 已覆盖：

- 每日启动前检查清单。
- 服务启动、端口、关闭、释放检查操作规程说明。
- 前置 payload 校准管理规则。
- 必须暂停试运行的触发条件。
- 回退流程。
- 管理员复核要点。

Step 266 的执行结果与 Step 264 一致：

- 在只读 preflight 阶段未启动服务。
- 在只读 preflight 阶段未向端口发起请求。
- 在只读 preflight 阶段未调用 endpoint。
- 对端口仅做只读监听状态检查。
- 对仓库、进程、路径、DOCX 迹象做只读核验。
- 未发生写入、证据化、评分化或正式链触发。

## 11. 与 Step 265 preflight 清单的一致性结论

Step 265 preflight 清单已覆盖：

- 启动前 Git 状态检查清单。
- 端口占用检查清单。
- 服务关闭检查项。
- 端口释放检查项。
- 管理员每日启动前与关闭后签核模板。
- preview-only / no-write / no-evidence 边界复核。
- 有效请求与前置校准计数规则。

Step 266 的执行结果与 Step 265 一致：

- 已核验 ZDoc / ZBid 仓库路径、分支、HEAD、clean 状态。
- 已确认建议端口在 Step 266 时点无监听。
- 已确认未发现疑似残留服务进程或 Ollama 进程。
- 已确认两仓未发现 `output/job/export` 路径。
- 已确认未发现本轮新增 DOCX 迹象。
- 未执行服务启动、端口访问请求、endpoint 调用或任何正式链动作。

## 12. 当前是否满足 20 人受控常态试运行启动前置条件

基于 Step 266 只读 preflight 结果，当前满足后续 20 人受控常态试运行的基础启动前置条件：

- ZDoc 仓库路径存在。
- ZDoc 分支、HEAD、clean 状态符合授权。
- ZBid 仓库路径存在。
- ZBid 分支、HEAD、clean 状态符合授权。
- `127.0.0.1:18766` 在 Step 266 时点无监听。
- `127.0.0.1:18767` 在 Step 266 时点无监听。
- 未发现疑似 ZDoc / ZBid 残留服务进程。
- 未发现 Ollama 相关运行进程。
- 两仓未发现 `output/job/export` 路径。
- 未发现本轮新增 DOCX 迹象。

但这不等于已授权启动。真正启动服务、访问端口、调用 endpoint、执行 smoke 或继续 observation-period，都必须进入后续步骤并由用户明确授权。

## 13. 仍未验证事项清单

仍未验证事项：

- 本 Step 267 未重新做端口监听检查，因为本步禁止端口访问。
- 本 Step 267 未启动 ZDoc 服务。
- 本 Step 267 未启动 ZBid 服务。
- 本 Step 267 未调用 preview-only endpoint。
- 本 Step 267 未做 startup-shutdown smoke。
- 本 Step 267 未做 observation-period controlled execution。
- 本 Step 267 未验证服务实际启动后的端口释放。
- 本 Step 267 未验证日志、问题清单、回退记录目录落地写入。
- 本 Step 267 未验证真实用户并发。
- 本 Step 267 未验证长期正式生产服务器运行。
- 本 Step 267 未验证 50 人正式部署。
- 本 Step 267 未验证顶级本地大模型升级。

## 14. 风险与观察项

风险与观察项：

- Step 266 的端口无监听结论只代表当时检查时点，未来启动前仍需再次只读确认。
- ZDoc 仓库存在历史 DOCX 文件，后续报告必须继续区分历史文件与本轮新增文件。
- 当前未发现专用试运行问题清单目录与回退记录目录，后续如需落地目录应先做授权。
- Step 267 为 docs-only 决策请求，不提供任何 runtime 可达性新证据。
- 当前主机仍只能作为 20 人试运行主机，不得自动提升为长期正式生产服务器。

## 15. 启动前管理员签核要求

后续若进入服务启动或 observation-period controlled execution，管理员必须在启动前签核：

- ZDoc 仓库路径、分支、HEAD、`git status --short`。
- ZBid 仓库路径、分支、HEAD、`git status --short`。
- 授权服务清单。
- 授权端口清单。
- 授权 endpoint 清单。
- 是否仅 preview-only / no-write / no-evidence。
- 是否禁止 `/generate`、`/export_docx`、`/review/apply`。
- 是否禁止 ZBid 写回。
- 是否禁止 DOCX 生成。
- 是否禁止 `output/job/export` 写入。
- 是否禁止 evidence 化。
- 是否禁止评分化。
- 是否禁止访问 `AI知识图谱大全` 文件夹。
- 前置 payload 校准是否单独计数、单独归档、不得混入有效请求。

没有管理员签核，不得启动。

## 16. 必须暂停启动的触发条件

出现以下任一情况，必须暂停启动：

- ZDoc 分支、HEAD 或 clean 状态不符合授权。
- ZBid 分支、HEAD 或 clean 状态不符合授权。
- 授权服务、端口或 endpoint 不明确。
- 端口已被未知进程占用。
- 发现疑似 ZDoc / ZBid 残留服务进程且无法解释。
- 发现 Ollama 进程但本轮未授权运行 Ollama。
- 发现 `output/job/export` 新增写入迹象。
- 发现本轮新增 DOCX 迹象。
- 任何正式链 flag 非 false。
- 需要调用 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回。
- 需要将 preview-only 结果作为 evidence 或评分依据。
- 需要访问 `AI知识图谱大全` 文件夹。

## 17. 回退条件

后续启动或试运行中出现以下情况，应立即回退：

- 服务启动后无法关闭。
- 端口无法释放。
- 调用了禁止 endpoint。
- 触发 ZBid 写回。
- 生成 DOCX。
- 写入 `output/job/export`。
- preview-only 结果被 evidence 化。
- preview-only 结果被评分化。
- 前置校准混入有效请求。
- 发生 fallback 到正式接口。
- 出现未知服务或未知端口访问。

回退后必须记录时间、角色、服务、PID、端口、endpoint、请求批次、payload 类型、问题分级、关闭状态、端口释放状态和是否需要单独授权修复。

## 18. 当前不得进入事项

当前不得进入：

- 50 人正式部署。
- 正式生产服务器定位。
- 顶级模型升级。
- 证据化。
- 评分化。
- ZBid 写回。
- 正式生成链。
- DOCX 导出链。
- review/apply 链。
- `output/job/export` 写入。
- 正式业务数据写入。

## 19. 后续可选路径

用户可在后续明确选择以下路径之一：

1. 执行服务启动关闭 smoke controlled execution。
   - 允许启动服务、访问授权端口、确认启动和关闭。
   - 必须单独授权。
   - 不得默认调用业务 endpoint，除非授权明确包含。

2. 继续 observation-period controlled execution。
   - 继续 20 人受控常态观察期验证。
   - 必须单独授权服务、端口、endpoint、请求数量和记录边界。

3. 先完善自动化测试方案。
   - 可先 docs-only 起草自动化边界测试方案。
   - 不启动服务、不访问端口、不调用 endpoint。

4. 暂停并进入人工复盘。
   - 汇总阶段结果、问题清单、观察项、回退记录和人工反馈。
   - 可保持 docs-only。

## 20. Step 268 授权请求草案

以下为可复制的 Step 268 授权请求草案。该草案不代表当前已授权执行 Step 268。

```text
执行 Step 268：ZDoc-ZBid 20-user service startup-shutdown smoke controlled execution

ZDoc 仓库：
/Users/youfeini/Desktop/文档生成系统

ZDoc 分支：
main

ZDoc 开始前 HEAD：
<填写 Step 267 结束后 HEAD>

ZBid 仓库：
/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean

ZBid 分支：
local-llm-integration-clean

ZBid 开始前 HEAD：
378355755372e03ac4f4064af59b287054984c25

特别说明：
不得访问、扫描、读取、复制、移动或分析 /Users/youfeini/Desktop/AI知识图谱大全。

授权范围：
1. 允许只读确认 ZDoc / ZBid 仓库路径、分支、HEAD、clean 状态。
2. 允许只读检查端口 18766 / 18767 是否占用。
3. 允许启动必要的 ZDoc preview-only 本地服务。
4. 允许启动必要的 ZBid preview-only receiver 本地服务。
5. 允许访问授权本地端口确认监听与关闭状态。
6. 允许记录启动命令、PID、端口、关闭结果和端口释放结果。
7. 仅允许新增 1 个 docs 报告文件。

严格禁止：
1. 不修改代码 / tests / frontend / backend / 既有 docs。
2. 不运行 Ollama。
3. 不调用任何 endpoint，除非用户在本授权中另行明确允许。
4. 不触发 /generate、/export_docx、/review/apply。
5. 不触发 ZBid 写回。
6. 不生成 DOCX。
7. 不写 output/job/export。
8. 不把 preview-only 结果作为 evidence。
9. 不把 preview-only 结果作为评分依据。
10. 不进入 50 人正式部署设计。
11. 不实施顶级模型升级。

完成后必须关闭本步启动服务，确认端口释放，提交 docs 报告后停止。
```
