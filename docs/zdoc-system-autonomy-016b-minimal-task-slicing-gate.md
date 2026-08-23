# SYSTEM-AUTONOMY-016B-MINIMAL-TASK-SLICING-GATE

## 当前基线确认

- 仓库根路径：`/Users/youfeini/Desktop/文档生成系统`
- 当前分支：`main`
- 起始 HEAD：`7e08a69bc2722297f80fe189aa8fd5b78f2cad5e`
- 起始 tag：`v0.1.686-system-autonomy-016a-repository-baseline-inventory-gate`
- 上一节点：`SYSTEM-AUTONOMY-016A-REPOSITORY-BASELINE-INVENTORY-GATE`
- 上一节点产物文件：`docs/zdoc-system-autonomy-016a-repository-baseline-inventory-gate.md`
- 当前工作区状态：起步检查时 `git status --short` 无输出，工作区 clean。

## 016B 节点定位

- 本节点为 `SYSTEM-AUTONOMY-016B` 后续任务最小切片门控。
- 本节点不是功能实现节点。
- 本节点不进入 `SYSTEM-AUTONOMY-016C`，不进入 `LOCAL-LAUNCHER-026`。
- 本节点仅基于 016A 的仓库基线盘点结果，将后续方向拆分为低风险、单节点、单目标、单仓库、可验收、可阻断的候选任务切片。

## 任务切片原则

- 单节点只解决 1 个明确目标。
- 单节点必须有明确允许文件清单。
- 单节点必须有明确禁止范围。
- 单节点必须有明确验收项。
- 单节点必须有异常停止条件。
- 禁止把盘点、设计、实现、测试、发布混在同一节点。
- 禁止自动跨入下一节点。
- 每个切片完成后必须停止并等待总控重新授权。

## 016A 候选方向复核

### 可继续 SYSTEM-AUTONOMY 链推进的方向

- `SYSTEM-AUTONOMY-016C`：可作为只读验收指标矩阵门控继续推进。
- `SYSTEM-AUTONOMY-016D`：可在 016C 之后形成风险阻断清单与回滚前置规则。
- 判断依据：016A 已确认 015A 至 015D 治理规则链，并推荐先完成任务切片，再决定是否进入任何实现或配置层。

### 需暂缓的方向

- `SYSTEM-AUTONOMY-017A`：低风险文档治理首节点应暂缓到 016C 与 016D 完成之后。
- `SYSTEM-AUTONOMY-017B`：文档治理验收与归档节点应暂缓到 017A 完成并回报之后。
- 判断依据：017A/017B 已接近具体治理执行，应先有验收指标矩阵和风险阻断规则作为前置约束。

### 必须独立专线处理的方向

- `LOCAL-LAUNCHER-026`：必须独立专线处理，不得从当前 `SYSTEM-AUTONOMY` 链条自动进入。
- 判断依据：015A 与 016A 均将 `LOCAL-LAUNCHER-026` 标记为 runtime / endpoint launcher 路线或独立专线方向。

### 当前禁止进入的方向

- runtime / endpoint / localhost / Ollama / 模型推理。
- prompt / 真实 KG / 真实项目资料 / secrets。
- output / job / export / log。
- 青天评标仓库：`/Users/youfeini/Desktop/ZhiFei_BizSystem`。
- 未授权的 `SYSTEM-AUTONOMY-016C` 或任何后续节点。
- 判断依据：015A 至 016A 均要求在未授权前不得进入实现、runtime、真实数据、launcher 或后续节点。

## 后续最小任务切片清单

以下切片仅为候选定义，不在本节点执行：

- `SYSTEM-AUTONOMY-016C`：只读验收指标矩阵门控。
- `SYSTEM-AUTONOMY-016D`：风险阻断清单与回滚前置规则门控。
- `SYSTEM-AUTONOMY-017A`：低风险文档治理首节点。
- `SYSTEM-AUTONOMY-017B`：文档治理验收与归档节点。
- `LOCAL-LAUNCHER-026`：独立专线，不得从当前链条自动进入。

## 候选切片定义

### SYSTEM-AUTONOMY-016C

- 节点名称：`SYSTEM-AUTONOMY-016C-READ-ONLY-ACCEPTANCE-MATRIX-GATE`
- 节点目标：基于 015A 至 016B 文档形成只读验收指标矩阵。
- 是否同一 Codex 对话框：原则上沿用当前 Codex 对话框，除非总控明确要求新开。
- 是否启用目标模式：启用。
- 允许文件范围：仅允许新增 `docs/zdoc-system-autonomy-016c-read-only-acceptance-matrix-gate.md`。
- 禁止范围：禁止代码、配置、测试、prompt、runtime、endpoint、localhost、Ollama、模型推理、真实 KG、真实项目资料、secrets、output、job、export、log、青天评标仓库、`LOCAL-LAUNCHER-026`。
- 质量检查方式：仅允许 `git diff --check`、`git diff --cached --check`、`git status --short`、`git diff --name-only`、`git diff --cached --name-only`。
- 提交与 tag 原则：仅 stage 授权文档，commit message 与 tag 必须由总控节点明确给出。
- 完成后是否自动进入下一节点：否。
- 异常停止条件：分支非 `main`、HEAD 不等于起始 HEAD、cwd 非目标仓库、工作区非 clean、出现非授权文件变化、push rejected、远端不一致、需要禁止命令、发现需要进入后续节点时立即停止。

### SYSTEM-AUTONOMY-016D

- 节点名称：`SYSTEM-AUTONOMY-016D-RISK-BLOCKER-AND-ROLLBACK-RULES-GATE`
- 节点目标：形成风险阻断清单与回滚前置规则，供后续文档治理或实现授权前使用。
- 是否同一 Codex 对话框：原则上沿用当前 Codex 对话框，除非总控明确要求新开。
- 是否启用目标模式：启用。
- 允许文件范围：仅允许新增 `docs/zdoc-system-autonomy-016d-risk-blocker-and-rollback-rules-gate.md`。
- 禁止范围：禁止代码、配置、测试、prompt、runtime、endpoint、localhost、Ollama、模型推理、真实 KG、真实项目资料、secrets、output、job、export、log、青天评标仓库、`LOCAL-LAUNCHER-026`。
- 质量检查方式：仅允许文档 diff 与工作区状态检查，不运行测试、编译、服务或模型相关命令。
- 提交与 tag 原则：仅 stage 授权文档，commit message 与 tag 必须由总控节点明确给出。
- 完成后是否自动进入下一节点：否。
- 异常停止条件：分支非 `main`、HEAD 不等于起始 HEAD、cwd 非目标仓库、工作区非 clean、出现非授权文件变化、push rejected、远端不一致、需要禁止命令、发现需要进入后续节点时立即停止。

### SYSTEM-AUTONOMY-017A

- 节点名称：`SYSTEM-AUTONOMY-017A-LOW-RISK-DOCUMENT-GOVERNANCE-FIRST-NODE`
- 节点目标：在明确授权文件清单后，进入首个低风险文档治理任务。
- 是否同一 Codex 对话框：由总控明确；若仍属于连续 `SYSTEM-AUTONOMY` 门控链，原则上沿用当前 Codex 对话框。
- 是否启用目标模式：启用。
- 允许文件范围：必须由总控明确 1 个或少量文档文件；未列入清单的文件不得读取内容、修改、stage、提交、删除或移动。
- 禁止范围：禁止代码、配置、测试、prompt、runtime、endpoint、localhost、Ollama、模型推理、真实 KG、真实项目资料、secrets、output、job、export、log、青天评标仓库、`LOCAL-LAUNCHER-026`。
- 质量检查方式：优先仅使用文档 diff 与工作区状态检查；如需其他检查，必须由总控显式授权。
- 提交与 tag 原则：仅提交授权文件，commit message 与 tag 必须由总控节点明确给出。
- 完成后是否自动进入下一节点：否。
- 异常停止条件：分支非 `main`、HEAD 不等于起始 HEAD、cwd 非目标仓库、工作区非 clean、出现非授权文件变化、授权文件清单不明确、需要禁止命令、发现需要进入 017B 或其他后续节点时立即停止。

### SYSTEM-AUTONOMY-017B

- 节点名称：`SYSTEM-AUTONOMY-017B-DOCUMENT-GOVERNANCE-ACCEPTANCE-AND-ARCHIVE-GATE`
- 节点目标：对 017A 的文档治理结果进行验收与归档说明。
- 是否同一 Codex 对话框：由总控明确；若仍属于连续 `SYSTEM-AUTONOMY` 门控链，原则上沿用当前 Codex 对话框。
- 是否启用目标模式：启用。
- 允许文件范围：必须由总控明确归档或验收文档文件；默认不得修改 017A 之外的文件。
- 禁止范围：禁止代码、配置、测试、prompt、runtime、endpoint、localhost、Ollama、模型推理、真实 KG、真实项目资料、secrets、output、job、export、log、青天评标仓库、`LOCAL-LAUNCHER-026`。
- 质量检查方式：仅使用总控授权的静态文档检查和 git 状态检查。
- 提交与 tag 原则：仅提交授权文件，commit message 与 tag 必须由总控节点明确给出。
- 完成后是否自动进入下一节点：否。
- 异常停止条件：分支非 `main`、HEAD 不等于起始 HEAD、cwd 非目标仓库、工作区非 clean、出现非授权文件变化、017A 结果无法确认、需要禁止命令、发现需要进入后续节点时立即停止。

### LOCAL-LAUNCHER-026

- 节点名称：`LOCAL-LAUNCHER-026`。
- 节点目标：独立专线处理 launcher 相关任务；目标必须由专线授权节点重新定义。
- 是否同一 Codex 对话框：不得由当前 `SYSTEM-AUTONOMY` 链条自动决定，必须由总控明确是否新开。
- 是否启用目标模式：必须由专线授权节点明确。
- 允许文件范围：必须由专线授权节点明确；当前节点不授权任何 launcher 文件。
- 禁止范围：当前 `SYSTEM-AUTONOMY` 链条不得进入 launcher 实现、runtime、endpoint、localhost、Ollama、模型推理或任何未授权文件。
- 质量检查方式：必须由专线授权节点另行定义。
- 提交与 tag 原则：必须由专线授权节点另行定义。
- 完成后是否自动进入下一节点：否。
- 异常停止条件：当前链条发现需要进入 `LOCAL-LAUNCHER-026` 时立即停止，等待独立专线授权。

## 推荐下一节点

推荐下一节点为 `SYSTEM-AUTONOMY-016C`。

推荐理由：先形成只读验收指标矩阵，明确每类后续节点的验收证据、禁止项和阻断条件，再决定是否进入风险阻断清单或文档治理首节点。

## 当前不得进入事项

- 不得进入 `LOCAL-LAUNCHER-026`。
- 不得进入 runtime / endpoint / localhost / Ollama / 模型推理。
- 不得进入 prompt / 真实 KG / 真实项目资料 / secrets。
- 不得进入 output / job / export / log。
- 不得进入青天评标仓库。
- 不得进入 `SYSTEM-AUTONOMY-016C` 或任何后续节点。

## 异常阻断规则

- 当前分支不是 `main`，立即停止。
- 当前 HEAD 不等于起始 HEAD，立即停止。
- cwd 不是目标仓库，立即停止。
- `git status --short` 非 clean，立即停止。
- 出现非授权文件变化，立即停止。
- 需要 fetch、pull、merge、rebase、reset、checkout、clean、stash 时，立即停止。
- push rejected 或远端不一致，立即停止。
- 发现需要进入 `LOCAL-LAUNCHER-026`、`SYSTEM-AUTONOMY-016C` 或其他后续节点，立即停止。

## 本节点验收标准

- 仅新增本文档 1 个授权文件。
- 不修改任何代码文件、配置文件、测试文件或 prompt 文件。
- 不运行测试、编译、服务、浏览器、localhost、runtime、endpoint、Ollama 或模型推理。
- 不触碰 prompt、真实 KG、真实项目资料、secrets、output、job、export、log。
- 不进入青天评标仓库。
- 不进入 `LOCAL-LAUNCHER-026`。
- 不进入 `SYSTEM-AUTONOMY-016C` 或任何后续节点。
- `git diff --check` 通过。
- `git diff --cached --check` 通过。
- 提交并创建 tag：`v0.1.687-system-autonomy-016b-minimal-task-slicing-gate`。
