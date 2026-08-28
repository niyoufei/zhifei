# 施组系统本地运行验收报告

## 最终结论

`PASS_LOCAL_RUNTIME_ACCEPTANCE`

## 2026-08-26 14:18 增量复验

| 增量验收项 | 结果 | 证据 |
|---|---:|---|
| 版本标签规范值 | PASS | 浏览器 DOM 标签和说明均为 A；根文档为 `zh-CN/translate=no/notranslate` |
| 中断原因定性 | PASS | Tender 同步阻塞触发旧监管器单次健康超时误判；事故前无模型尝试或生成 run |
| Tender `file_id` 正文缓存复用 | PASS | 4/4 缓存正文完整性验证通过，源解析器调用 0 次 |
| 事件循环隔离 | PASS | 路径解析与规则矩阵均移入工作线程 |
| 监管器抗瞬断 | PASS | 普通探测失败至少 3 次且持续 15 秒；真实身份不匹配仍立即停止 |
| 新封存真实接口复验 | PASS | 4 个 `file_id`，HTTP 200，0.2096 秒 |
| 解析期间健康响应 | PASS | 14/14 成功，p95 33.2 ms，最大 138.2 ms |
| 进程稳定性 | PASS | supervisor/backend/UI 无重启，失败计数 0，`CLOSE_WAIT` 0 |
| 新增全量回归 | PASS | 3457 passed、1 skipped、0 failed |
| 桌面启动身份链 | PASS | 桌面 app → 外置 bootstrap → `release-27ce1033097e93bf27c895be` |

当前运行身份：

- release：`release-27ce1033097e93bf27c895be`
- source digest：`27ce1033097e93bf27c895beb8b59e5a34721626380c3daba8df49c1d6d9f26c`
- manifest digest：`b3875915f77688a246aad6f59754b68493fcc6087fe4f17d85ca33ddda675a7c`
- runtime digest：`b60770ac265dabd6d4f9e179ab7b573b6b8e06db74d8574fd4f898497578a72f`
- bootstrap：`ok=true, running=true, status=healthy`
- 任务：active/queued/running/stale 均为 0

增量证据目录：`artifacts/runtime_acceptance/runtime-remediation-20260826-141829/`。

`PASS_LOCAL_RUNTIME_ACCEPTANCE`

验收时间：2026-08-26（Asia/Shanghai）
验收标识：`runtime-acceptance-20260826-124300`

## 验收结果

| 验收项 | 结果 | 最终证据 |
|---|---:|---|
| 完整测试不少于 3261 | PASS | 3449 passed、1 skipped、0 failed |
| 静态与导入副作用 | PASS | 589 源文件 compile、19 Shell、diff-check、隔离导入测试 |
| 34 文件、268 MiB 冷导入 | PASS | 2.260 s，门槛 136 s |
| 全缓存重复导入 | PASS | 2.221 s，34/34 cache hit，门槛 30 s |
| 导入时 health p95 | PASS | 最大 66.3 ms，门槛 500 ms |
| 第二轮可控瓶颈优化 | PASS | 冷处理阶段 1.799→0.874 s，下降 51.42% |
| 文件级状态与强制资料阻断 | PASS | Tender 1/1；损坏 BoQ 0/1，`MANDATORY_SOURCE_REJECTED`，未进入模型 |
| PDF 原生崩溃隔离与预览缓存 | PASS | spawn 子进程、内容寻址预览、稳定 warning |
| Tender/BoQ file_id 契约 | PASS | 持久 file_id 复用、重复 query 参数兼容 |
| 幽灵任务回收 | PASS | queued/running 超时转 interrupted_recoverable，不重放模型 |
| 失败进度与检查点真实性 | PASS | 历史失败恢复为 75%、6/6 持久章节、稳定证据阻断码 |
| 浏览器中文错误 | PASS | `INPUT_INVALID`、`MANDATORY_SOURCE_REJECTED`，无连接栈/密钥 |
| 浏览器刷新恢复 | PASS | URL job_id 恢复持久终态并在终态清理 query |
| 系统级监管 | PASS | LaunchAgent → bootstrap → supervisor → backend/UI 唯一父子链 |
| 不可变版本身份 | PASS | current、manifest、source、runtime、health 五项完全一致 |
| 桌面仅启动最新版本 | PASS | 桌面 app 仅调用外置 bootstrap，不引用工作区 |
| 真实模型两章实跑 | PASS | 2/2 非空、2 检查点、峰值并发 1、2 次尝试 |
| 实跑后持续 CLOSE_WAIT | PASS | 稳定超过 60 秒后应用侧 0 |
| 本地服务保持运行 | PASS | 8010/8501 healthy，active/queued/running/stale 均为 0 |

## 全量自动化

- 命令：`.venv/bin/python -m pytest -q`
- collected：3450
- passed：3449
- skipped：1（既有明确跳过）
- failed：0
- warnings：15（第三方弃用、测试进程 fork 和既有 Pydantic `.dict()` 警告）
- elapsed：63.34 秒

故障矩阵覆盖成功、超时、429、5xx、有限重试、备用路由、熔断、取消、预算耗尽、部分失败、检查点失败、心跳合并、幽灵任务、`.doc` 转换、缓存版本、sidecar 篡改、强制资料阻断、PDF 隔离、接口契约、监管熔断和不可变切换恢复。

## 性能对比

| 阶段 | 冷导入 | 冷处理 | 热导入 | 热处理 | health p95 最大 |
|---|---:|---:|---:|---:|---:|
| 监测故障基线 | 272.000 s | 未分段 | 未测 | 未测 | 未测 |
| 第一轮封存 | 3.102 s | 1.799 s | 2.319 s | 1.395 s | 86.832 ms |
| 第二轮最终封存 | 2.260 s | 0.874 s | 2.221 s | 0.855 s | 66.300 ms |

第二轮根据累计耗时从高到低选择占比超过 10% 的处理路径。大正文从 JSON 拆入带完整性校验的 sidecar 后，冷处理下降 51.42%，热处理下降 38.71%；相对事故基线，最终冷导入缩短约 99.17%。

## 浏览器端验收

- 最终页面正常渲染并可检查后端连接。
- 合成 Tender 被文件级任务接受；伪造损坏的合成 BoQ 被明确拒绝，页面显示 `MANDATORY_SOURCE_REJECTED：强制资料存在未解析文件，已阻止进入生成。`，没有调用模型。
- 空白会话点击生成显示 `INPUT_INVALID：请至少上传 1 个招标文件/答疑`，不展示 RuntimeError、HTTPConnectionPool 或调用栈。
- 以历史任务 ID 刷新页面后，UI 从鉴权状态接口恢复任务，显示 failed、75% 和 `REQUIREMENT_EVIDENCE_BLOCKED`；终态后 URL 自动回到无 job_id 状态。
- 自动化测试同时覆盖 running/queued/succeeded/failed/interrupted 的恢复白名单、非法 ID、快照错配和终态清理。

## 真实模型小规模验收

- 运行 ID：`real-model-06b7942c0e74`
- 输入：两段脱敏合成市政排水章节，不含当前真实项目资料。
- 主路由：Anthropic `claude-opus-5`；备用：Anthropic `claude-sonnet-5`。
- 限制：并发 1；每章最多主/备各一次；总请求输出上限 16,384 tokens；硬截止 720 秒。
- 实际：2 次主路由调用，备用 0 次；请求预算 8192/16384；峰值并发 1；总耗时 132.703 秒。
- 章节：2/2 成功，字符数 2044/2272，各有独立 SHA-256 和检查点。
- 检查点：`draft_complete`，saved_chapter_count=2，binding digest `9290e3564e94f8d73db0cb63552aab52a90a3559a63ee4612fdba1d151456a7d`。
- 凭据：复用现有本地配置；未打印、复制或写入报告；证据扫描未发现疑似密钥形态。

## 最终封存与运行状态

- release：`release-036e5820ddbc376f8df40359`
- source digest：`036e5820ddbc376f8df40359ea373af33ee2a1ec4b97ed529f731d877a69621f`
- runtime digest：`b60770ac265dabd6d4f9e179ab7b573b6b8e06db74d8574fd4f898497578a72f`
- manifest digest：`0bbffc599b2e33d49373db07c438cc35913312214bf89624656fd90f13bb2781`
- supervisor/backend/UI PID：16152/19928/19929
- 任务：active 0、queued 0、running 0、stale 0、total 37
- 外置 bootstrap `--status`：`ok=true, running=true, status=healthy`
- `/p0/readiness`：`runtime_ready=true`；`release_ready=false` 仅因工作树 dirty。

桌面应用和 LaunchAgent 都只经外置 bootstrap 解析 `current.json/current`，因此以后构建新封存版本时按钮无需由用户判断路径；如果身份、清单、运行时依赖或当前指针不一致，启动器会拒绝混用。

## 发布边界

本结论仅表示当前 macOS 本地运行验收通过。未提交、未推送、未创建 PR；dirty 工作树不影响本地运行，但仍阻断正式发布就绪。Linux/systemd 尚未达到同等级不可变启动验收。

`PASS_LOCAL_RUNTIME_ACCEPTANCE`
