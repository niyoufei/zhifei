# 施组系统运行整改报告

## 最终结论

`PASS_LOCAL_RUNTIME_ACCEPTANCE`

## 2026-08-26 14:18 运行中断增量整改

用户截图中的版本标签显示“一个”，不是系统把版本 A 改成了中文，也不是数据损坏。应用内部始终保存规范值 `A`；原因是原 Streamlit 页面声明为英文，Chrome 将孤立字母 A 当作英语不定冠词翻译成“一个”。页面现在在首屏建立 `lang=zh-CN`、`translate=no`、`notranslate` 和 Google no-translate 元数据，浏览器实测标签及说明均稳定显示 `A`。

14:18 和 14:24 的突然停止也不是模型供应商故障。导入任务均为 4/4 成功、4/4 缓存命中，但旧 Tender 接口没有把导入阶段的正文缓存传给解析器，214 页 PDF 被再次读取，随后约 8.9 秒的规则矩阵同步占用 FastAPI 事件循环。旧监管器的健康超时仅 2 秒，并把一次超时统一误报为 `SUPERVISOR_BACKEND_IDENTITY_MISMATCH`，立即同时终止后端和 UI，因此页面看起来像“工作中突然停止”。事故窗口内没有模型尝试、生成 run 或检查点，也没有 macOS 崩溃报告。

增量修复包括：对 `file_id` 的解析器版本、源 SHA、缓存摘要和 sidecar SHA 做完整校验后直接传递已提取正文；路径解析和 Tender 规则阶段移入工作线程；监管器区分超时、拒绝连接、HTTP、无效响应与真实五项身份不匹配；普通健康瞬断至少连续 3 次且持续 15 秒才允许重启，真实身份不匹配仍立即 fail-closed；健康接口新增降级、失败次数和稳定错误码。

新不可变封存为 `release-27ce1033097e93bf27c895be`，source/manifest/runtime digest 分别为 `27ce1033097e93bf27c895beb8b59e5a34721626380c3daba8df49c1d6d9f26c`、`b3875915f77688a246aad6f59754b68493fcc6087fe4f17d85ca33ddda675a7c`、`b60770ac265dabd6d4f9e179ab7b573b6b8e06db74d8574fd4f898497578a72f`。桌面主应用只调用外置 bootstrap；bootstrap 状态为 `ok=true, running=true, status=healthy`，不引用可变工作区。

同一批 4 个真实持久 `file_id` 在新封存上完成接口复验：HTTP 200、0.2096 秒；并发采集 14 次健康检查全部成功，p95 33.2 ms、最大 138.2 ms，backend/UI PID 均稳定，监管失败计数为 0。全量回归为 3457 passed、1 skipped、0 failed，目标回归 146 passed、0 failed，Python 编译与 `git diff --check` 均通过，应用侧 `CLOSE_WAIT` 为 0。

增量证据位于 `artifacts/runtime_acceptance/runtime-remediation-20260826-141829/`。当前 `runtime_ready=true`；`release_ready=false` 仍仅表示来源工作树有受保护的未提交改动，不影响这份内容寻址封存的本地运行。

`PASS_LOCAL_RUNTIME_ACCEPTANCE`

本轮已按“证据质量门前移 → 模型供应商准入 → 系统级进程监管 → 不可变版本封存”的顺序完成整改、两轮优化、全量回归、浏览器验收和小规模真实模型验收。桌面按钮及 LaunchAgent 现在只会启动当前内容寻址的封存版本，不再从可变工作区直接运行。

## 现场保护

- 工作区：`/Users/fei/Desktop/zhifei-phase2-writable-recovery-R34/zhifei`
- 基线 HEAD：`b60dd79d2a1557f2754294082e74d1b09e459894`
- 分支：`codex/professional-render-reliability`
- 保留了既有未提交改动、项目资料、检查点、事件和运行数据。
- 未执行 reset、checkout、批量清理、commit、push、pull、fetch 或 PR 操作。
- 测试使用隔离合成资料；真实模型验收未发送当前真实项目资料。
- 最终 `git status --porcelain` 有 127 个条目；dirty 状态已绑定到发布来源并如实显示，但不阻断本地运行。

## 故障为何反复出现

反复故障不是单一文件格式问题，而是五个失效域叠加：

1. PDF 首图预览在 API 主进程内调用原生 PDFium。原生段错误不能被 Python 异常捕获，导致 8010 后端退出，而 Streamlit 仍存活，于是页面持续出现 `Connection refused`。
2. Tender/BoQ、上传和生成入口对 `file_id`、同步/异步任务及必传资料成功条件理解不一致，部分失败会被误显示为成功。
3. 模型调用在供应商可用性证明之前进入长重试；失败章节、进度、心跳和检查点由多处覆盖，形成 75%/100% 假进度及错误终态。
4. 任务依赖请求生命周期，服务重启后缺少持久恢复与幽灵任务回收。
5. 桌面按钮直接指向可变工作区，没有系统级父进程监管和不可变身份链，用户无法确认新旧版本。

彻底修复采用的是隔离、准入、持久状态、监管和内容寻址封存的组合，而不是继续增加无界重试。

## 已完成整改

### 证据与终态真实性

- 招标要求证据门已前移；强制资料未成功解析时禁止进入生成。
- 运行状态统一为 `queued/running/succeeded/failed/cancelled/interrupted_recoverable`，同时记录 `phase` 与 `work_state`。
- 章节分别统计 started/succeeded/failed/total；失败章节不再计入成功进度。
- 心跳、提供商尝试、预算、错误和章节快照采用字段合并，终态不会覆盖过程证据。
- 检查点按真实持久化结果写为 `draft_complete/failed_partial/failed_empty/interrupted_recoverable`；禁止 `draft_complete + section_count=0`。
- 失败终态不显示成功式 100%，页面仅显示稳定错误码、中文说明和建议动作。

### 模型供应商准入与可靠性

- 所有生成入口在模型调用前执行新鲜、凭据绑定的供应商准入。
- 常规章节并发固定为 2；受限真实验收并发固定为 1。
- 流式调用区分连接、首 token、空闲流、单请求和单章节期限。
- 超时立即切换备用路由；仅 429/可恢复 5xx 允许一次有限退避，不突破章节总期限。
- 连续可归因失败打开熔断器；公共状态仅返回脱敏原因和剩余期限。
- 客户端显式关闭；真实验收结束 60 秒后应用侧持续 `CLOSE_WAIT` 为 0。
- 取消后停止新章节并保留已成功检查点。

### 导入、PDF 隔离、缓存和接口契约

- 新增持久异步导入接口 `POST /ingest/jobs`、`GET /ingest/jobs/{job_id}`，返回文件级状态、耗时、页数、缓存命中、warnings 和 rejected。
- 完整 SHA-256 作为 `file_id`；Tender、BoQ 和后续知识导入复用同一存储与解析结果。
- Tender/BoQ 明确接收可重复 query `file_id`，前后端契约一致。
- PDF 预览在最多 2 个 `spawn` 隔离进程中执行，失败只降级当前文件；预览按内容摘要复用缓存。
- `.doc` 先由 LibreOffice 无界面转换，工具缺失、转换失败或超时均返回明确阻断码。
- 单文件 100 MiB、单批 40 文件或 512 MiB、单文件解析 180 秒；长解析持续刷新心跳。
- 招标/答疑/清单任一失败即阻止生成；可选资料可降级但必须列出。
- 第二轮将不小于 256 KiB 的提取正文从 JSON 元数据拆为 UTF-8 sidecar；文件名、字节数和 SHA-256 全部校验。缺失、截断或同长度篡改均安全判为缓存失效，旧内联缓存继续兼容。

### 生命周期、可观测性和刷新恢复

- 生成与导入由本地持久队列执行，不依赖请求生命周期。
- 启动扫描 queued/running；超过 60 秒无有效心跳的任务转为 `interrupted_recoverable`，不自动重放模型请求。
- 结构化追加事件覆盖导入、路由切换、重试、熔断、检查点、取消和终态，并统一脱敏与轮转。
- `/health` 返回构建/发布身份、进程监管、队列和任务统计；`/p0/readiness` 分离 runtime_ready 与 release_ready。
- Streamlit 创建任务后仅把合法 32 位 job_id 写入 URL。刷新后先通过后端身份与操作鉴权，再从持久任务快照恢复最小状态；非法 ID、快照错配和未知状态 fail-closed，终态清理 URL。
- 浏览器实测恢复历史失败任务 `8d3752f97c904a88b4577f098baf8762`，显示 `REQUIREMENT_EVIDENCE_BLOCKED` 和 75% 真实进度，随后清除 query 参数。

### 系统级监管与不可变版本

- macOS LaunchAgent `com.youfeini.docgen.runtime-supervisor` 只执行外置 bootstrap：`/usr/bin/python3 -I -B .../bootstrap/launch_current.py --supervise`。
- 监管器为后端和 Streamlit 的唯一父进程，连续崩溃会持久计数并打开熔断，不会无限拉起。
- 外置 bootstrap、current.json、current symlink、源码清单、Python venv 和非系统 Mach-O 依赖形成反向可验证身份链。
- 源码和运行时普通文件/目录只读；密钥文件保持 0600；状态和日志目录保持 0700。
- 桌面 `/Users/fei/Desktop/施组专家系统.app` 只调用外置 bootstrap，含 `-I -B`，不引用工作区或 `current/scripts`。原按钮已保存为带时间戳的可恢复备份。
- 最终当前版本：`release-036e5820ddbc376f8df40359`。
- 五项身份：
  - build SHA：`b60dd79d2a1557f2754294082e74d1b09e459894`
  - source digest：`036e5820ddbc376f8df40359ea373af33ee2a1ec4b97ed529f731d877a69621f`
  - runtime digest：`b60770ac265dabd6d4f9e179ab7b573b6b8e06db74d8574fd4f898497578a72f`
  - manifest digest：`0bbffc599b2e33d49373db07c438cc35913312214bf89624656fd90f13bb2781`
  - system id：`docgen-system`

## 验证与两轮优化

- 全量回归：3449 passed、1 skipped、0 failed，63.34 秒。
- 589 个 Python 源文件通过无写盘编译；19 个 Shell 脚本通过语法检查；`git diff --check` 通过。
- 首轮等效压力语料：34 个有效 UTF-8 合成文件，精确 268,434,954 字节；冷 3.102 秒、热 2.319 秒、健康 p95 最大 86.832 ms。
- 处理阶段是最大的可控路径，冷态占 58%。第二轮后冷态处理 1.799→0.874 秒（下降 51.42%），热态处理 1.395→0.855 秒（下降 38.71%）。
- 最终整段冷导入 2.260 秒、热导入 2.221 秒，34/34 成功、热态 34/34 缓存命中，健康 p95 最大 66.3 ms。
- 相对监测基线 272 秒，最终冷导入缩短约 99.17%。

## 真实模型验收

- 运行：`real-model-06b7942c0e74`。
- 仅使用脱敏合成市政排水项目提示，不发送当前真实项目资料。
- 路由：主 Anthropic `claude-opus-5`；备用 Anthropic `claude-sonnet-5`。
- 并发 1；实际 2 次主路由尝试，备用未调用；请求输出预算 8192/16384 tokens。
- 两章均一次成功，正文字符数 2044/2272；报告仅保存字符数和 SHA-256，不展示正文。
- 两个独立检查点均成功，最终 `draft_complete`、saved_chapter_count=2；总耗时 132.703 秒。
- `credentials_exposed=false`，交付目录扫描未发现疑似密钥形态。

## 最终运行状态与边界

- Supervisor PID 16152、backend PID 19928、Streamlit PID 19929；旧工作区和上一发布版本运行进程均为 0。
- 8010/8501 正常监听；`active=queued=running=stale=0`，总持久任务 37。
- `runtime_ready=true`；`release_ready=false` 的唯一原因是 `worktree_not_clean`。
- 当前封存是 macOS 本地交付。Linux/systemd 模板未纳入同等级不可变启动验收。
- 0555/0444 防止普通误改，但同一账号仍可主动 chmod；内容摘要、反向验签与系统监管用于发现并拒绝篡改。
- 源来源绑定到 dirty 状态与 source digest，不能仅凭 HEAD 重建；这不影响当前本地封存身份的可核验性。

## 交付证据

- `artifacts/runtime_acceptance/runtime-acceptance-20260826-124300/timeline.json`
- `artifacts/runtime_acceptance/runtime-acceptance-20260826-124300/runtime_snapshot.json`
- `artifacts/runtime_acceptance/runtime-acceptance-20260826-124300/performance.json`
- `artifacts/runtime_acceptance/runtime-acceptance-20260826-124300/performance_after.json`
- `artifacts/runtime_acceptance/runtime-acceptance-20260826-124300/performance_comparison.json`
- `artifacts/runtime_acceptance/runtime-acceptance-20260826-124300/test_checklist.json`
- `artifacts/runtime_acceptance/runtime-acceptance-20260826-124300/real_model_acceptance.json`
- `artifacts/runtime_acceptance/runtime-acceptance-20260826-124300/worktree_protection.json`

`PASS_LOCAL_RUNTIME_ACCEPTANCE`
