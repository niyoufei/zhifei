# SYSTEM-AUTONOMY-017A-LOW-RISK-DOCUMENT-GOVERNANCE-INDEX-GATE

## 当前基线确认

- 仓库根路径：`/Users/youfeini/Desktop/文档生成系统`
- 当前 git root：`/Users/youfeini/Desktop/文档生成系统`
- 当前分支：`main`
- 起始 HEAD：`4569c763f8ca145e6607d9fe02289a4ee5157d62`
- 起始 tag：`v0.1.689-system-autonomy-016d-failsafe-rollback-matrix-gate`
- 上一节点名称：`SYSTEM-AUTONOMY-016D-FAILSAFE-AND-ROLLBACK-MATRIX-GATE`
- 上一节点产物文件：`docs/zdoc-system-autonomy-016d-failsafe-and-rollback-matrix-gate.md`
- 当前工作区状态：起步检查时 `git status --short` 无输出，工作区 clean。

## 017A 节点定位

- 本节点为 `SYSTEM-AUTONOMY-017A` 低风险文档治理索引门控。
- 本节点是文档治理执行节点，用于新增一个 `SYSTEM-AUTONOMY` 文档治理索引与执行入口说明文件。
- 本节点不是功能实现节点。
- 本节点不改变 015A 至 016D 既有治理链内容，仅新增当前索引文件。
- 本节点不进入 `SYSTEM-AUTONOMY-017B`。
- 本节点不进入 `LOCAL-LAUNCHER-026`。

## SYSTEM-AUTONOMY 当前治理链索引

| 节点编号 | 节点名称 | 节点定位 | 产物文件 | 对应 tag | 对后续工作的约束作用 |
| --- | --- | --- | --- | --- | --- |
| 015A | `SYSTEM-AUTONOMY-015A-SCOPE-AUTHORIZATION-DOCUMENT-GATE` | 授权范围门控 | `docs/zdoc-system-autonomy-015-scope-and-authorization-gate.md` | `v0.1.682-system-autonomy-015-scope-authorization-gate` | 明确未授权直接进入实现，将 launcher 路线划为独立专线，建立禁止区域边界。 |
| 015B | `SYSTEM-AUTONOMY-015B-TASK-CLARIFICATION-GATE` | 任务明确化门控 | `docs/zdoc-system-autonomy-015b-task-clarification-gate.md` | `v0.1.683-system-autonomy-015b-task-clarification-gate` | 固化任务目标、执行对象、禁止项、后续节点进入条件和 cwd 偏差防控。 |
| 015C | `SYSTEM-AUTONOMY-015C-EXECUTION-RULES-GATE` | 执行规则固化门控 | `docs/zdoc-system-autonomy-015c-execution-rules-gate.md` | `v0.1.684-system-autonomy-015c-execution-rules-gate` | 固化 Codex 对话框连续性、目标模式、仓库边界、文件变更、禁止命令、异常停止和完成回报。 |
| 015D | `SYSTEM-AUTONOMY-015D-ACCEPTANCE-AND-HANDOFF-GATE` | 验收闭环与交接门控 | `docs/zdoc-system-autonomy-015d-acceptance-and-handoff-gate.md` | `v0.1.685-system-autonomy-015d-acceptance-handoff-gate` | 将 015A 至 015D 收口为后续节点执行前的治理基线，要求后续节点重新声明目标、仓库、文件和禁止范围。 |
| 016A | `SYSTEM-AUTONOMY-016A-REPOSITORY-BASELINE-INVENTORY-GATE` | 仓库基线盘点与后续任务候选映射门控 | `docs/zdoc-system-autonomy-016a-repository-baseline-inventory-gate.md` | `v0.1.686-system-autonomy-016a-repository-baseline-inventory-gate` | 以只读方式建立仓库基线、受保护区域和后续候选方向的文件名级索引。 |
| 016B | `SYSTEM-AUTONOMY-016B-MINIMAL-TASK-SLICING-GATE` | 后续任务最小切片门控 | `docs/zdoc-system-autonomy-016b-minimal-task-slicing-gate.md` | `v0.1.687-system-autonomy-016b-minimal-task-slicing-gate` | 将后续方向拆成低风险、单节点、单目标、单仓库、可验收、可阻断的候选切片。 |
| 016C | `SYSTEM-AUTONOMY-016C-READONLY-ACCEPTANCE-METRIC-GATE` | 只读验收指标矩阵门控 | `docs/zdoc-system-autonomy-016c-readonly-acceptance-metric-gate.md` | `v0.1.688-system-autonomy-016c-readonly-acceptance-metric-gate` | 将 cwd、git root、branch、HEAD、tag、工作区、暂存区、文件变更、禁止行为和回报完整性转化为可审计验收指标。 |
| 016D | `SYSTEM-AUTONOMY-016D-FAILSAFE-AND-ROLLBACK-MATRIX-GATE` | 异常阻断与回滚前置机制矩阵门控 | `docs/zdoc-system-autonomy-016d-failsafe-and-rollback-matrix-gate.md` | `v0.1.689-system-autonomy-016d-failsafe-rollback-matrix-gate` | 将异常发现、立即停止、禁止自行修复、回滚前置判断、总控复核和恢复条件转化为前置规则。 |

## 治理链形成的能力清单

- 授权边界控制能力：通过 015A 明确是否允许进入实现、runtime、launcher 或其他专线。
- 任务边界明确能力：通过 015B 要求后续节点先明确目标、执行对象、禁止项和进入条件。
- Codex 对话框与仓库一一对应能力：通过 015C、016D 固化当前 Codex 对话框必须对应目标仓库，禁止错仓库执行。
- 目标模式约束能力：通过 015C 及后续节点要求目标模式只执行当前节点，不自动扩展。
- 单节点单文件变更能力：通过 015B 至 016D 持续要求每个节点具备明确授权文件清单，未授权文件不得修改、stage 或提交。
- 禁止区域防护能力：通过 015A 至 016D 持续保护 runtime、endpoint、localhost、Ollama、模型推理、prompt、真实 KG、真实项目资料、secrets、output、job、export、log、青天评标仓库和 launcher 专线。
- 验收矩阵判定能力：通过 016C 将基线、文件变更、禁止行为、节点推进和完成回报转化为矩阵化验收标准。
- 异常阻断能力：通过 016D 明确 cwd、git root、branch、HEAD、status、非授权文件、push、tag 和远端异常的立即停止规则。
- 回滚前置判断能力：通过 016D 明确回滚不是默认动作，只能在总控复核后依据污染类型另行处理。
- 后续节点切片能力：通过 016B 将 017A、017B、LOCAL-LAUNCHER-026 等方向拆分为候选，不允许自动进入。

## 文档治理索引规则

后续 `SYSTEM-AUTONOMY` 文档治理节点必须满足以下规则：

- 每个节点必须明确目标仓库。
- 每个节点必须明确是否新开 Codex 对话框。
- Codex 对话框必须与目标仓库一一对应。
- 每个节点必须明确是否启用目标模式。
- 每个节点必须明确允许文件清单。
- 每个节点必须明确禁止范围。
- 每个节点必须明确质量检查方式。
- 每个节点必须明确 commit message 与 tag。
- 每个节点完成后必须停止，不得自动进入下一节点。

## 当前受保护区域索引

以下区域当前仍不得进入、不得读取内容、不得修改：

- runtime。
- endpoint。
- localhost。
- Ollama。
- 模型推理。
- prompt。
- 真实 KG。
- 真实项目资料。
- secrets。
- output。
- job。
- export。
- log。
- 青天评标仓库：`/Users/youfeini/Desktop/ZhiFei_BizSystem`。
- `LOCAL-LAUNCHER-026`。

## 后续可执行任务索引

以下仅列候选，不在本节点执行：

- `SYSTEM-AUTONOMY-017B`：文档治理验收与归档节点。
- `SYSTEM-AUTONOMY-018A`：治理索引扩展或文档目录规范化候选节点。
- `LOCAL-LAUNCHER-026`：独立专线，当前禁止自动进入。

## 017B 前置进入条件

进入 `SYSTEM-AUTONOMY-017B` 前，至少必须满足：

- 017A 完成并提交。
- 017A tag 已创建并推送。
- `origin/main` 指向 017A 完成 HEAD。
- 工作区 clean。
- 暂存区 clean。
- 未修改 015A 至 016D 既有节点文档。
- 未触碰代码、runtime、prompt、真实数据、output、log。
- Codex 对话框仍对应文档生成系统仓库：`/Users/youfeini/Desktop/文档生成系统`。
- 总控确认 017A 可收口。

## 当前不得进入事项

- 不得进入 `LOCAL-LAUNCHER-026`。
- 不得进入 `SYSTEM-AUTONOMY-017B` 或后续节点。
- 不得进入青天评标仓库。
- 不得进入 runtime / endpoint / localhost / Ollama / 模型推理。
- 不得进入 prompt / 真实 KG / 真实项目资料 / secrets。
- 不得进入 output / job / export / log。

## 最终收口说明

- 017A 完成后，`SYSTEM-AUTONOMY` 将形成首个低风险文档治理索引入口。
- 017A 不改变 015A 至 016D 既有治理链内容，仅新增索引文件。
- 017A 完成后不得自动进入 `SYSTEM-AUTONOMY-017B` 或 `LOCAL-LAUNCHER-026`。

## 本节点验收标准

- 仅新增本文档 1 个授权文件。
- 不修改 015A 至 016D 既有节点文档。
- 不修改任何代码文件、配置文件、测试文件或 prompt 文件。
- 不运行测试、编译、服务、浏览器、localhost、runtime、endpoint、Ollama 或模型推理。
- 不触碰 prompt、真实 KG、真实项目资料、secrets、output、job、export、log。
- 不进入或修改青天评标仓库。
- 不进入 `LOCAL-LAUNCHER-026`。
- 不进入 `SYSTEM-AUTONOMY-017B` 或任何后续节点。
- `git diff --check` 通过。
- `git diff --cached --check` 通过。
- 提交并创建 tag：`v0.1.690-system-autonomy-017a-low-risk-document-governance-index-gate`。
