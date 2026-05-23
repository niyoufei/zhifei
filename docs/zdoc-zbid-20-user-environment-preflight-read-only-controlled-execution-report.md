# ZDoc-ZBid 20-user environment preflight read-only controlled execution report

## 1. Step 266 执行摘要

Step 266 按 20 人受控常态试运行的环境预检要求完成只读检查。本次执行仅做仓库、分支、HEAD、工作区、端口监听、疑似残留进程、Ollama 进程、`output/job/export`、DOCX 迹象、日志 / 问题 / 回退目录，以及 Step 264 / Step 265 手册一致性的只读核验。

本次未启动 ZDoc 服务，未启动 ZBid 服务，未运行 Ollama，未访问端口发起请求，未调用任何 endpoint，未触发 `/generate`、`/export_docx`、`/review/apply`，未触发 ZBid 写回，未生成 DOCX，未写 `output/job/export`，未将 preview-only 结果作为 evidence 或评分依据，未进入 50 人正式部署设计，未实施顶级模型升级。

## 2. 检查时间

- 检查时间：`2026-05-23 13:35:31 +0800`
- 检查方式：只读命令检查。
- 端口检查方式：`lsof` 只读检查监听状态；未向端口发送 HTTP 请求。

## 3. ZDoc 仓库检查结果

| 检查项 | 预期 | 实际 | 结论 |
| --- | --- | --- | --- |
| 仓库路径 | `/Users/youfeini/Desktop/文档生成系统` | 存在 | 通过 |
| 当前分支 | `main` | `main` | 通过 |
| 当前 HEAD | `01820af738fe5abd513b9deb4687dca801a7ae86` | `01820af738fe5abd513b9deb4687dca801a7ae86` | 通过 |
| `git status --short` | 空 | 空 | clean |
| 目标报告文件 | 不存在 | 执行前不存在 | 通过 |

ZDoc 仓库满足本次只读 preflight 的分支、HEAD 与 clean 状态要求。

## 4. ZBid 仓库检查结果

| 检查项 | 预期 | 实际 | 结论 |
| --- | --- | --- | --- |
| 仓库路径 | `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean` | 存在 | 通过 |
| 当前分支 | `local-llm-integration-clean` | `local-llm-integration-clean` | 通过 |
| 当前 HEAD | `378355755372e03ac4f4064af59b287054984c25` | `378355755372e03ac4f4064af59b287054984c25` | 通过 |
| `git status --short` | 空 | 空 | clean |

ZBid 仓库满足本次只读 preflight 的路径、分支、HEAD 与 clean 状态要求。本步骤未在 ZBid 仓库 commit、tag、push。

## 5. 端口占用检查结果

端口检查仅使用 `lsof -nP -iTCP:<port> -sTCP:LISTEN` 读取监听状态，未发起 HTTP 请求，未调用 endpoint。

| 端口 | 检查结果 | 结论 |
| --- | --- | --- |
| `127.0.0.1:18766` | 无监听输出 | 未被占用 |
| `127.0.0.1:18767` | 无监听输出 | 未被占用 |

结论：建议端口当前均无监听，占用检查通过。

## 6. 残留进程检查结果

只读进程检查未发现疑似 ZDoc / ZBid 残留服务进程。

检查范围包括：

- `uvicorn`
- `app.main:app`
- 当前 ZDoc 仓库路径相关命令
- ZBid clean 仓库路径相关命令

结果：无匹配输出。未发现疑似残留服务。

## 7. Ollama 进程检查结果

只读进程检查未发现 Ollama 相关运行进程。

结果：无匹配输出。

结论：本步骤未运行 Ollama，也未发现当前正在运行的 Ollama 相关进程。

## 8. 禁止路径 output/job/export 检查结果

| 仓库 | 检查路径 | 结果 | 结论 |
| --- | --- | --- | --- |
| ZDoc | `output/job/export` | `MISSING` | 未发现该路径 |
| ZBid | `output/job/export` | `MISSING` | 未发现该路径 |

结论：两仓均未发现 `output/job/export` 路径。本步骤未写入该路径。

## 9. DOCX 生成迹象检查结果

ZDoc 仓库存在历史 `.docx` 文件，包含根目录、`frontend_web/`、`projects/`、`backend/`、`exports/`、`build/`、`venv/` 等历史文件位置。ZBid 仓库本次未列出 `.docx` 文件。

本步骤的判断口径：

- `git status --short -- '*.docx' output job export build exports projects backend/build backend/data/uploads` 在 ZDoc 仓库无输出。
- 同一检查在 ZBid 仓库无输出。
- 本步骤未运行服务、未调用 endpoint、未生成 DOCX。

结论：存在历史 DOCX 文件不等于本步骤新增 DOCX；本步骤未发现新增 DOCX 文件迹象。

## 10. 日志目录状态

ZDoc 仓库只读检查发现非 `.git` 日志相关目录：

- `./logs`
- `./backup/runtime-artifacts/output/smoke_logs`

ZBid 仓库在本次目录模式检查中未发现运行日志目录。

结论：ZDoc 已存在可作为参考的日志目录；ZBid 未发现同类运行日志目录。后续真实试运行如需保存日志，应在用户授权范围内明确日志落点，不得写入正式业务数据。

## 11. 问题清单目录状态

ZDoc 仓库本次未发现独立的问题清单运行目录。

ZBid 仓库发现：

- `./.github/ISSUE_TEMPLATE`

该目录是 GitHub issue 模板目录，不等同于 20 人受控常态试运行的问题清单归档目录。

结论：当前未发现专用试运行问题清单目录。后续若要落地问题清单，应在授权步骤中明确仅写入 docs 报告或指定非正式记录位置。

## 12. 回退记录目录状态

ZDoc 仓库本次未发现独立回退记录目录。

ZBid 仓库本次未发现独立回退记录目录。

结论：当前未发现专用回退记录目录。后续如需建立回退记录目录或文件，必须另行授权，不得在本步骤创建。

## 13. AI知识图谱大全 文件夹未访问声明

用户已暂停 `/Users/youfeini/Desktop/AI知识图谱大全` 文件夹识别任务。

本步骤未访问、扫描、读取、复制、移动、分析或识别该文件夹。本步骤所有文件系统读取均限定在：

- `/Users/youfeini/Desktop/文档生成系统`
- `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- `/Users/youfeini/.codex/memories/MEMORY.md`

## 14. 与 Step 264 管理员 SOP 的一致性检查

Step 264《20-user controlled routine operation handbook and administrator SOP》已包含以下关键章节：

- 每日启动前检查清单。
- 服务启动、端口、关闭、释放检查操作规程说明。
- 前置 payload 校准管理规则。
- 必须暂停试运行的触发条件。
- 回退流程。

本次 Step 266 检查与 Step 264 一致：

- 未在 docs-only 阶段启动服务。
- 未在 docs-only 阶段访问端口发起请求。
- 未在 docs-only 阶段调用 endpoint。
- 对端口只做只读监听检查。
- 对前置条件做只读核验，不做运行修复。

## 15. 与 Step 265 preflight 清单的一致性检查

Step 265《20-user environment preflight checklist and startup-shutdown control archive》已包含以下关键章节：

- 启动前 Git 状态检查清单。
- 端口占用检查清单。
- 服务关闭检查项。
- 端口释放检查项。
- 管理员每日启动前与关闭后签核模板。

本次 Step 266 检查与 Step 265 一致：

- 已核验 ZDoc / ZBid 仓库路径、分支、HEAD、clean 状态。
- 已只读检查 `127.0.0.1:18766` 与 `127.0.0.1:18767` 监听状态。
- 已只读检查疑似残留服务进程与 Ollama 进程。
- 已检查 `output/job/export` 路径。
- 已检查 DOCX 新增迹象。
- 未执行任何服务启动、关闭或 endpoint 调用。

## 16. 启动前置条件是否满足

从本次只读 preflight 角度看，后续受控试运行的基础前置条件当前满足：

- ZDoc 仓库路径存在。
- ZDoc 分支、HEAD 与授权一致。
- ZDoc 工作区 clean。
- ZBid 仓库路径存在。
- ZBid 分支、HEAD 与授权一致。
- ZBid 工作区 clean。
- `127.0.0.1:18766` 当前未被占用。
- `127.0.0.1:18767` 当前未被占用。
- 未发现疑似 ZDoc / ZBid 残留服务进程。
- 未发现 Ollama 相关运行进程。
- 两仓未发现 `output/job/export` 路径。
- 未发现本步骤新增 DOCX 迹象。

启动前仍需注意：

- 真正启动服务、访问端口、调用 endpoint 必须由 Step 267 或后续步骤单独授权。
- 日志、问题清单、回退记录的专用落点尚未形成统一目录，后续若需要写入必须单独授权。

## 17. 风险与观察项

风险与观察项：

- ZDoc 仓库存在历史 DOCX 文件，后续报告必须继续区分历史文件与本轮新增文件。
- 当前未发现专用试运行问题清单目录和回退记录目录；后续若要落地目录，应先设计 docs-only 方案并另行授权。
- 端口当前无监听，但后续真实启动前仍需再次检查。
- 当前检查只证明 preflight 时点状态，不代表未来服务启动后状态。
- 当前检查不代表正式生产服务器准备完成。

## 18. 是否建议进入 Step 267

建议可以进入 Step 267 的授权请求或 stage review，但不得自动进入。

Step 267 可选方向：

1. 起草 Step 266 的 stage review。
2. 起草下一轮受控试运行启动授权请求。
3. 起草日志 / 问题清单 / 回退记录目录落点设计。
4. 起草端口与服务启动关闭记录模板细化文档。

无论选择哪一方向，均必须继续保持 preview-only / no-write / no-evidence，并由用户明确授权。

## 19. Step 267 授权请求草案

以下为可复制的 Step 267 授权请求草案。该草案不代表当前已授权执行 Step 267。

```text
执行 Step 267：ZDoc-ZBid 20-user environment preflight execution stage review and next action authorization request

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<填写 Step 266 结束后 HEAD>

特别说明：
不得访问、扫描、读取、复制、移动、分析或识别 /Users/youfeini/Desktop/AI知识图谱大全。

本步性质：
docs-only / stage-review-only / no-code-change / no-service / no-port-access / no-endpoint-call / no-writeback

目标：
归档 Step 266 只读环境预检结果，并提出下一步授权建议。

允许新增文件：
docs/<填写 Step 267 目标文档名>.md

严格禁止：
1. 不修改代码 / tests / frontend / backend / 既有 docs。
2. 不运行 ZDoc 服务。
3. 不运行 ZBid 服务。
4. 不运行 Ollama。
5. 不访问端口。
6. 不调用任何 endpoint。
7. 不触发 /generate、/export_docx、/review/apply。
8. 不触发 ZBid 写回。
9. 不生成 DOCX。
10. 不写 output/job/export。
11. 不把 preview-only 结果作为 evidence。
12. 不把 preview-only 结果作为评分依据。
13. 不进入 50 人正式部署设计。
14. 不实施顶级模型升级。

文档必须复核：
- Step 266 是否只读检查 ZDoc / ZBid 仓库、分支、HEAD、clean 状态。
- 端口 18766 / 18767 是否无监听。
- 是否存在残留服务进程或 Ollama 进程。
- output/job/export 与 DOCX 新增迹象检查结果。
- 日志、问题清单、回退记录目录观察项。
- 是否仍需单独授权才能启动服务、访问端口或调用 endpoint。

完成后必须停止，不得自动进入后续步骤。
```
