# ZDoc-ZBid preview-only error message guidance

## 1. 使用范围

本文档用于解释 ZDoc-ZBid preview-only / no-write / no-evidence 小范围试用中的常见错误提示。

本文档只用于人工理解和留痕，不授权现场修复、不授权切换到正式链、不授权启动服务或调用 endpoint。

## 2. 常见错误分类

### disabled

含义：preview-only outbound、receiver 或相关能力处于关闭状态。

人工处理建议：

- 记录提示原文。
- 确认本次是否有明确授权启用 preview-only 能力。
- 未授权时不得启用。
- 不允许切换到 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回。

### not configured

含义：缺少必要配置，例如 receiver endpoint 未配置。

人工处理建议：

- 记录缺失配置名称。
- 停止本次试用或 smoke。
- 另行申请配置边界授权。
- 不得写入 `.env`、配置文件或持久配置，除非用户另行授权。

### configured_not_sent

含义：已配置 endpoint，但 network-send 未显式启用，因此未发送。

人工处理建议：

- 这是 default-off 边界的正常保护结果。
- 记录当前配置状态。
- 如确需发送，必须确认用户已明确授权临时启用 preview-only network-send。
- 不得通过 fallback 调用正式接口。

### blocked

含义：payload、配置、flag 或 receiver 规则阻止继续处理。

人工处理建议：

- 阅读 `blocked_reasons`。
- 判断是否属于输入问题、配置问题、边界问题或正式链风险。
- 任一正式链风险出现时立即停止。
- 不得现场修复，修复必须另行授权。

### validation error

含义：输入校验不通过，可能缺少字段、字段类型错误，或违反 preview-only / no-write / no-evidence 边界。

人工处理建议：

- 记录校验错误。
- 不把校验结果当作评分结论。
- 不把 advisory 或 preview 当作 evidence。
- 如需调整输入结构，另行申请修复授权。

### receiver unreachable

含义：ZBid receiver endpoint 不可达、连接失败、超时或服务未启动。

人工处理建议：

- 记录 endpoint、时间和错误摘要。
- 停止试用。
- 不得改用其他 ZBid endpoint。
- 不得改用正式链接口。
- 如需重启服务或更换端口，必须另行授权。

## 3. 统一禁止

发生任何错误时均不得：

- 现场切换到正式链。
- 触发 `/generate`。
- 触发 `/export_docx`。
- 触发 `/review/apply`。
- 触发 ZBid 写回。
- 生成 DOCX。
- 写 `output/job/export`。
- 将 preview-only 结果作为 evidence。
- 将 preview-only 结果作为评分依据。
- 写入正式业务数据。

## 4. 失败记录留痕

失败记录应包含：

- 时间。
- 操作者角色。
- 操作入口。
- 错误分类。
- 错误原文或摘要。
- `blocked_reasons`。
- 是否保持五个 false flags。
- 是否停止。
- 是否需要另行授权。

失败记录不得写入正式业务数据，不得包含敏感业务数据，不得作为正式 evidence 或评分依据。
