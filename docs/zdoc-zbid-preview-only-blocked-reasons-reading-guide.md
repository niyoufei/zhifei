# ZDoc-ZBid preview-only blocked_reasons reading guide

## 1. blocked_reasons 的用途

`blocked_reasons` 用于解释 preview-only / no-write / no-evidence 链路为什么不能继续进入正式生成、正式 evidence、正式评分依据、DOCX 导出、review/apply 或 ZBid 写回。

`blocked_reasons` 是边界提示和排查线索，不是正式 evidence，不是评分依据，不是正式业务结论。

## 2. 常见 blocked_reasons 类型

### preview-only 边界类

示例：

- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

含义：当前结果只能用于 preview-only 人工观察，不允许写回、不允许作为 evidence、不允许作为评分依据。

### 人工复核类

示例：

- `small_scale_trial_requires_human_review`

含义：当前结果需要人工复核，不能自动进入正式链。

### 配置类

可能表现为 endpoint 未配置、network-send 未启用、能力 disabled。

判断方法：

- 查看是否有 `disabled`、`not configured`、`configured_not_sent`、`endpoint_missing`、`network_send_not_enabled` 等含义。
- 这通常表示能力被安全关闭或缺少授权配置。

### 输入类

可能表现为缺少必要字段、字段类型错误、payload 不符合 preview-only 要求。

判断方法：

- 查看是否提到 missing、invalid、must be mapping、must be list 等含义。
- 这通常需要修正输入结构，但修正必须另行授权。

### 边界类

可能表现为 no-write / no-evidence / preview-only 状态不成立。

判断方法：

- 查看 `preview_only`、`no_write`、`no_evidence` 是否为 true。
- 查看五个 false flags 是否均为 false。

### 正式链风险类

可能表现为生成、导出、review/apply、ZBid 写回、output/job/export 写入、evidence、评分依据等风险。

判断方法：

- 发现 `/generate`、`/export_docx`、`/review/apply`、writeback、DOCX、evidence、score、output/job/export 等相关提示时，按正式链风险处理。

## 3. 何时停止

出现以下情况立即停止：

- 任一 false flag 非 false。
- `preview_only` 不是 true。
- `no_write` 不是 true。
- `no_evidence` 不是 true。
- 出现正式链风险类 blocked reason。
- 出现未知 endpoint 调用。
- 出现 DOCX、ZBid 写回、evidence、评分依据或 `output/job/export` 写入。

停止后只记录事实，不得现场修复。

## 4. 何时上报

以下情况应上报：

- 不理解的 blocked reason。
- 同一 blocked reason 重复出现。
- 配置类 blocked reason 影响试用继续。
- 输入类 blocked reason 需要调整 payload。
- 试用人员无法理解 blocked reason 含义。
- 任一正式链风险提示。

## 5. 何时申请单独修复授权

以下情况需要单独修复授权：

- 需要修改代码。
- 需要修改 UI 文案。
- 需要修改日志结构。
- 需要修改 backend adapter 或 receiver 行为。
- 需要修改 endpoint。
- 需要启动服务、访问端口或重新试用验证。

## 6. 不得作为 evidence 或评分依据

`blocked_reasons` 只说明当前 preview-only 链路为什么停止或为什么需要人工复核。

不得将 `blocked_reasons` 用作：

- 正式 evidence。
- 正式评分依据。
- 正式投标成果内容。
- ZBid 写回依据。
- DOCX 正文或附件依据。
