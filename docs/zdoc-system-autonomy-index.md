# SYSTEM-AUTONOMY Document Governance Index

## 索引文件定位

- 本文件为 `SYSTEM-AUTONOMY` 文档治理链正式索引文件。
- 本文件只记录已完成节点事实，包括节点编号、节点名称、产物文件、commit、tag、节点类型、完成状态、边界和后续衔接。
- 本文件不替代任何既有节点文档；每个节点的权威内容仍以对应 `docs/zdoc-system-autonomy-*` 文档和完成 tag 为准。
- 本文件不修改历史结论，不移动 tag，不改写 commit 历史。
- 本文件不构成功能实现授权，不授权代码、配置、测试、prompt、runtime、endpoint、localhost、Ollama、模型推理、真实 KG、真实项目资料、secrets、output、job、export 或 log 相关动作。

## 当前基线确认

- 仓库根路径：`/Users/youfeini/Desktop/文档生成系统`
- 当前 git root：`/Users/youfeini/Desktop/文档生成系统`
- 当前分支：`main`
- 起始 HEAD：`ac1cd656cb7684f10f86f874a8c7a8f6efdcfefa`
- 起始 tag：`v0.1.694-system-autonomy-018c-document-directory-index-candidate-gate`
- 上一节点名称：`SYSTEM-AUTONOMY-018C-DOCUMENT-DIRECTORY-INDEX-CANDIDATE-GATE`
- 上一节点产物文件：`docs/zdoc-system-autonomy-018c-document-directory-index-candidate-gate.md`
- 当前工作区状态：起步检查时 `git status --short` 无输出，工作区 clean。

## SYSTEM-AUTONOMY 节点总索引表

| 节点编号 | 节点名称 | 节点类型 | 产物文件 | commit hash | tag | 完成状态 | 是否文档节点 | 是否功能实现节点 | 是否修改代码 | 是否触碰受保护区域 | 后续约束作用 | 下一节点建议或衔接节点 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 015A | `SYSTEM-AUTONOMY-015A-SCOPE-AUTHORIZATION-DOCUMENT-GATE` | 授权范围门控 | `docs/zdoc-system-autonomy-015-scope-and-authorization-gate.md` | `ba22cbf` | `v0.1.682-system-autonomy-015-scope-authorization-gate` | 已完成 | 是 | 否 | 否 | 否 | 确认未授权直接进入实现，将 launcher 路线划为独立专线，并建立禁止区域边界。 | 015B |
| 015B | `SYSTEM-AUTONOMY-015B-TASK-CLARIFICATION-GATE` | 任务明确化门控 | `docs/zdoc-system-autonomy-015b-task-clarification-gate.md` | `626300a` | `v0.1.683-system-autonomy-015b-task-clarification-gate` | 已完成 | 是 | 否 | 否 | 否 | 固化任务目标、执行对象、禁止项、后续节点进入条件和 cwd 偏差防控。 | 015C |
| 015C | `SYSTEM-AUTONOMY-015C-EXECUTION-RULES-GATE` | 执行规则固化门控 | `docs/zdoc-system-autonomy-015c-execution-rules-gate.md` | `3d0c4f5` | `v0.1.684-system-autonomy-015c-execution-rules-gate` | 已完成 | 是 | 否 | 否 | 否 | 固化 Codex 对话框连续性、目标模式、仓库边界、文件变更、禁止命令、异常停止和完成回报。 | 015D |
| 015D | `SYSTEM-AUTONOMY-015D-ACCEPTANCE-AND-HANDOFF-GATE` | 验收闭环与交接门控 | `docs/zdoc-system-autonomy-015d-acceptance-and-handoff-gate.md` | `a65530d` | `v0.1.685-system-autonomy-015d-acceptance-handoff-gate` | 已完成 | 是 | 否 | 否 | 否 | 将 015A 至 015D 收口为后续节点执行前的治理基线。 | 016A |
| 016A | `SYSTEM-AUTONOMY-016A-REPOSITORY-BASELINE-INVENTORY-GATE` | 仓库基线盘点门控 | `docs/zdoc-system-autonomy-016a-repository-baseline-inventory-gate.md` | `7e08a69` | `v0.1.686-system-autonomy-016a-repository-baseline-inventory-gate` | 已完成 | 是 | 否 | 否 | 否 | 以只读方式建立仓库基线、受保护区域和后续候选方向的文件名级索引。 | 016B |
| 016B | `SYSTEM-AUTONOMY-016B-MINIMAL-TASK-SLICING-GATE` | 后续任务最小切片门控 | `docs/zdoc-system-autonomy-016b-minimal-task-slicing-gate.md` | `64deae6` | `v0.1.687-system-autonomy-016b-minimal-task-slicing-gate` | 已完成 | 是 | 否 | 否 | 否 | 将后续方向拆成低风险、单节点、单目标、单仓库、可验收、可阻断的候选切片。 | 016C |
| 016C | `SYSTEM-AUTONOMY-016C-READONLY-ACCEPTANCE-METRIC-GATE` | 只读验收指标矩阵门控 | `docs/zdoc-system-autonomy-016c-readonly-acceptance-metric-gate.md` | `570ad73` | `v0.1.688-system-autonomy-016c-readonly-acceptance-metric-gate` | 已完成 | 是 | 否 | 否 | 否 | 将 cwd、git root、branch、HEAD、tag、工作区、暂存区、文件变更、禁止行为和回报完整性转化为可审计验收指标。 | 016D |
| 016D | `SYSTEM-AUTONOMY-016D-FAILSAFE-AND-ROLLBACK-MATRIX-GATE` | 异常阻断与回滚前置机制门控 | `docs/zdoc-system-autonomy-016d-failsafe-and-rollback-matrix-gate.md` | `4569c76` | `v0.1.689-system-autonomy-016d-failsafe-rollback-matrix-gate` | 已完成 | 是 | 否 | 否 | 否 | 将异常发现、立即停止、禁止自行修复、回滚前置判断、总控复核和恢复条件转化为前置机制。 | 017A |
| 017A | `SYSTEM-AUTONOMY-017A-LOW-RISK-DOCUMENT-GOVERNANCE-INDEX-GATE` | 低风险文档治理索引门控 | `docs/zdoc-system-autonomy-017a-low-risk-document-governance-index-gate.md` | `1d6e6d4` | `v0.1.690-system-autonomy-017a-low-risk-document-governance-index-gate` | 已完成 | 是 | 否 | 否 | 否 | 形成首个低风险文档治理索引入口，集中记录治理链、能力清单、索引规则和受保护区域。 | 017B |
| 017B | `SYSTEM-AUTONOMY-017B-DOCUMENT-GOVERNANCE-ACCEPTANCE-AND-ARCHIVE-GATE` | 文档治理验收归档门控 | `docs/zdoc-system-autonomy-017b-document-governance-acceptance-and-archive-gate.md` | `b4a8285` | `v0.1.691-system-autonomy-017b-document-governance-acceptance-archive-gate` | 已完成 | 是 | 否 | 否 | 否 | 验收 017A 产物并归档 015A 至 017A 治理链，形成“索引入口 + 验收归档”小闭环。 | 018A |
| 018A | `SYSTEM-AUTONOMY-018A-DOCUMENT-DIRECTORY-NORMALIZATION-PLAN-GATE` | 文档目录规范化方案门控 | `docs/zdoc-system-autonomy-018a-document-directory-normalization-plan-gate.md` | `44b2693` | `v0.1.692-system-autonomy-018a-document-directory-normalization-plan-gate` | 已完成 | 是 | 否 | 否 | 否 | 基于文件名级盘点形成文档目录规范化目标、问题识别和后续候选切片，不执行实际目录调整。 | 018B |
| 018B | `SYSTEM-AUTONOMY-018B-DOCUMENT-DIRECTORY-NORMALIZATION-FREEZE-GATE` | 文档目录规范化冻结门控 | `docs/zdoc-system-autonomy-018b-document-directory-normalization-freeze-gate.md` | `f67c472` | `v0.1.693-system-autonomy-018b-document-directory-normalization-freeze-gate` | 已完成 | 是 | 否 | 否 | 否 | 验收并冻结 018A 方案，明确后续目录索引新增、重命名、分层或归档调整必须另设节点。 | 018C |
| 018C | `SYSTEM-AUTONOMY-018C-DOCUMENT-DIRECTORY-INDEX-CANDIDATE-GATE` | 文档目录索引文件候选方案门控 | `docs/zdoc-system-autonomy-018c-document-directory-index-candidate-gate.md` | `ac1cd65` | `v0.1.694-system-autonomy-018c-document-directory-index-candidate-gate` | 已完成 | 是 | 否 | 否 | 否 | 形成正式目录索引文件的候选定位、命名方案、字段设计、内容边界和执行前置条件。 | 019A |

## 已完成治理链能力摘要

- 授权边界控制：015A 确认未授权直接进入实现，并将 `LOCAL-LAUNCHER-026` 划为独立专线。
- 任务明确化：015B 固化任务目标、执行对象、禁止项和后续节点进入条件。
- 执行规则固化：015C 固化 Codex 对话框连续性、目标模式、cwd 起步确认、仓库边界、文件变更、禁止命令、异常停止和完成回报。
- 验收闭环与交接：015D 将 015A 至 015D 收口为后续节点执行前的治理基线。
- 仓库基线盘点：016A 以只读方式建立仓库结构、受保护区域和后续候选方向的文件名级盘点。
- 任务最小切片：016B 将后续方向拆为低风险、单节点、单目标、单仓库、可验收、可阻断的候选切片。
- 只读验收指标矩阵：016C 将基线、文件变更、禁止行为、节点推进和完成回报转化为可审计验收指标。
- 异常阻断与回滚前置判断：016D 固化异常发现、立即停止、禁止自行修复、回滚前置判断、总控复核和恢复条件。
- 文档治理索引入口：017A 形成首个低风险文档治理索引入口。
- 文档治理验收归档：017B 验收 017A 产物并归档 015A 至 017A 治理链。
- 目录规范化方案：018A 基于 docs 文件名级盘点形成目录规范化方案。
- 目录规范化冻结：018B 对 018A 方案完成验收和冻结。
- 目录索引候选方案：018C 形成正式目录索引文件的候选定位、命名、字段和执行前置条件。

## 受保护区域索引

以下区域仍不得进入、不得读取内容、不得修改：

- runtime
- endpoint
- localhost
- Ollama
- 模型推理
- prompt
- 真实 KG
- 真实项目资料
- secrets
- output
- job
- export
- log
- 青天评标仓库：`/Users/youfeini/Desktop/ZhiFei_BizSystem`
- `LOCAL-LAUNCHER-026`

## Codex 对话框与仓库一一对应规则

- 文档生成系统节点必须在选择 `/Users/youfeini/Desktop/文档生成系统` 的 Codex 对话框中执行。
- 青天评标系统节点必须在选择 `/Users/youfeini/Desktop/ZhiFei_BizSystem` 的 Codex 对话框中执行。
- 不得在一个仓库对应的 Codex 对话框中通过 `cd` 切换到另一个仓库执行节点。
- 若需要切换仓库，必须新建对应仓库的 Codex 对话框。
- 指令框上方必须提示：是否需要新开 Codex 对话框、是否启用目标模式、目标仓库。
- 每个节点开始前必须先确认 `pwd`、git root、branch、HEAD、tag 和工作区状态。

## 后续节点进入规则

- 当前索引文件完成后不得自动进入 `SYSTEM-AUTONOMY-019B`。
- `SYSTEM-AUTONOMY-019B` 必须作为目录索引验收归档节点单独执行。
- `LOCAL-LAUNCHER-026` 必须独立专线处理，当前 `SYSTEM-AUTONOMY` 链条不得自动进入。
- 后续任何功能实现节点必须另行建立更严格的授权文件清单和测试边界。
- 后续任何目录调整、文件重命名、文件移动，必须另设专项节点。
- 后续节点必须重新声明目标、允许文件、禁止范围、质量检查、commit message、tag 和完成回报格式。

## 019B 前置进入条件

进入 `SYSTEM-AUTONOMY-019B` 前，至少必须满足：

- 019A 完成并提交。
- 019A tag 已创建并推送。
- `origin/main` 指向 019A 完成 HEAD。
- 远端 tag 指向 019A 完成 HEAD。
- 工作区 clean。
- 暂存区 clean。
- 仅新增 `docs/zdoc-system-autonomy-index.md`。
- 未修改 015A 至 018C 既有节点文档。
- 未实际重命名、移动、删除、改写任何既有文档。
- 未触碰代码、runtime、prompt、真实数据、output、log。
- 当前 Codex 对话框仍对应文档生成系统仓库：`/Users/youfeini/Desktop/文档生成系统`。
- 总控明确授权进入 019B，且 019B 重新列出允许文件、禁止范围、检查命令、commit message、tag 和完成回报格式。

## 当前不得进入事项

- 不得进入 `LOCAL-LAUNCHER-026`。
- 不得进入 `SYSTEM-AUTONOMY-019B` 或任何后续节点。
- 不得进入青天评标仓库。
- 不得进入 runtime / endpoint / localhost / Ollama / 模型推理。
- 不得进入 prompt / 真实 KG / 真实项目资料 / secrets。
- 不得进入 output / job / export / log。
- 不得实际重命名、移动、删除或改写任何既有文档。

## 最终收口说明

- 019A 完成后，`SYSTEM-AUTONOMY` 将拥有正式文档目录索引入口。
- 019A 仅新增索引文件，不改变任何既有文件。
- 019A 完成后不得自动进入 `SYSTEM-AUTONOMY-019B` 或 `LOCAL-LAUNCHER-026`。

## 本索引维护边界

- 本文件后续如需更新，必须由总控另设节点并明确允许修改本文件。
- 本文件不得被用于直接修订历史节点文档。
- 本文件不得被用于绕过节点级授权、质量检查、提交、tag 或完成回报规则。
