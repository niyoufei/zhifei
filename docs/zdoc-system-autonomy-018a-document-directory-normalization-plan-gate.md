# SYSTEM-AUTONOMY-018A-DOCUMENT-DIRECTORY-NORMALIZATION-PLAN-GATE

## 当前基线确认

- 仓库根路径：`/Users/youfeini/Desktop/文档生成系统`
- 当前 git root：`/Users/youfeini/Desktop/文档生成系统`
- 当前分支：`main`
- 起始 HEAD：`b4a828595fa9ea5f144b1bf35b107bb480800a90`
- 起始 tag：`v0.1.691-system-autonomy-017b-document-governance-acceptance-archive-gate`
- 上一节点名称：`SYSTEM-AUTONOMY-017B-DOCUMENT-GOVERNANCE-ACCEPTANCE-AND-ARCHIVE-GATE`
- 上一节点产物文件：`docs/zdoc-system-autonomy-017b-document-governance-acceptance-and-archive-gate.md`
- 当前工作区状态：起步检查时 `git status --short` 无输出，工作区 clean。

## 018A 节点定位

- 本节点为 `SYSTEM-AUTONOMY-018A` 文档目录规范化方案门控。
- 本节点只基于 015A 至 017B 已形成的治理链，对 `docs/` 目录中的 `SYSTEM-AUTONOMY` 文档进行文件名、节点顺序、目录组织、归档方式和后续规范化切片的方案化梳理。
- 本节点只做方案，不做实际目录调整。
- 本节点不是功能实现节点。
- 本节点不重命名、移动、删除、改写任何既有文档。
- 本节点不修改任何代码、配置、测试、prompt、runtime、endpoint、localhost、Ollama、模型推理、真实 KG、真实项目资料、secrets、output、job、export 或 log。
- 本节点不进入 `SYSTEM-AUTONOMY-018B`。
- 本节点不进入 `LOCAL-LAUNCHER-026`。

## 015A 至 017B 治理链归档基础

- `SYSTEM-AUTONOMY-015A`：授权范围门控，确认未授权直接进入实现，并将 `LOCAL-LAUNCHER-026` 标记为 runtime / endpoint launcher 独立路线。
- `SYSTEM-AUTONOMY-015B`：任务明确化门控，固化任务目标、执行对象、禁止项、后续进入条件和 cwd 偏差防控。
- `SYSTEM-AUTONOMY-015C`：执行规则固化门控，固化同一 Codex 对话框、目标模式、仓库边界、文件变更、禁止命令、异常停止和完成回报。
- `SYSTEM-AUTONOMY-015D`：验收闭环与交接门控，将 015A 至 015D 收口为后续节点执行前的治理基线。
- `SYSTEM-AUTONOMY-016A`：仓库基线盘点与后续任务候选映射门控，以只读和文件名级方式识别仓库结构、受保护区域和后续候选方向。
- `SYSTEM-AUTONOMY-016B`：后续任务最小切片门控，将后续方向拆分为低风险、单节点、单目标、单仓库、可验收、可阻断的候选切片。
- `SYSTEM-AUTONOMY-016C`：只读验收指标矩阵门控，将 cwd、git root、branch、HEAD、tag、文件变化、禁止行为和回报完整性转化为可审计验收指标。
- `SYSTEM-AUTONOMY-016D`：异常阻断与回滚前置机制矩阵门控，将异常发现、立即停止、禁止自行修复、回滚前置判断、总控复核和恢复条件转化为前置机制。
- `SYSTEM-AUTONOMY-017A`：低风险文档治理索引门控，形成当前治理链的首个文档治理索引入口。
- `SYSTEM-AUTONOMY-017B`：文档治理验收与归档门控，验收 017A 产物并归档 015A 至 017A 治理链，形成“索引入口 + 验收归档”的文档治理小闭环。

## docs 目录现状文件名级别盘点

本节仅基于允许的只读命令结果进行文件名级别盘点；未读取内容的文件不作内容判断，不打开受保护区域内容，不改写、移动、重命名任何文件。

### SYSTEM-AUTONOMY 文件名级别可见清单

- 早期目标模式治理链：
  - `docs/zdoc-system-autonomy-goal-mode-governance-and-roadmap-gate-system-autonomy-001.md`
  - `docs/zdoc-system-autonomy-goal-mode-task-decomposition-gate-system-autonomy-002.md`
  - `docs/zdoc-system-autonomy-goal-mode-permission-matrix-and-state-machine-gate-system-autonomy-003.md`
  - `docs/zdoc-system-autonomy-goal-mode-codebase-read-only-inventory-authorization-gate-system-autonomy-004.md`
  - `docs/zdoc-system-autonomy-goal-mode-code-change-proposal-gate-system-autonomy-005.md`
- 静态守卫与 revalidation 链：
  - `docs/zdoc-system-autonomy-controlled-code-implementation-no-runtime-gate-system-autonomy-006.md`
  - `docs/zdoc-system-autonomy-static-validation-only-gate-system-autonomy-007.md`
  - `docs/zdoc-system-autonomy-007-fix-1-static-guard-path-blocklist-correction-no-runtime.md`
  - `docs/zdoc-system-autonomy-007-revalidation-1-static-validation-only-gate.md`
  - `docs/zdoc-system-autonomy-008-scope-and-authorization-gate.md`
  - `docs/zdoc-system-autonomy-008-implementation-static-guard-scope-correction-no-runtime.md`
  - `docs/zdoc-system-autonomy-008-revalidation-1-static-validation-only-gate.md`
  - `docs/zdoc-system-autonomy-009-scope-and-authorization-gate.md`
  - `docs/zdoc-system-autonomy-009-implementation-static-guard-scope-correction-no-runtime.md`
  - `docs/zdoc-system-autonomy-009-revalidation-1-static-validation-only-gate.md`
  - `docs/zdoc-system-autonomy-010-scope-and-authorization-gate.md`
  - `docs/zdoc-system-autonomy-010-implementation-static-guard-scope-correction-no-runtime.md`
  - `docs/zdoc-system-autonomy-010-revalidation-1-static-validation-only-gate.md`
  - `docs/zdoc-system-autonomy-011-scope-and-authorization-gate.md`
  - `docs/zdoc-system-autonomy-011-implementation-static-guard-scope-correction-no-runtime.md`
  - `docs/zdoc-system-autonomy-011-revalidation-static-validation-only-gate.md`
  - `docs/zdoc-system-autonomy-012-scope-and-authorization-gate.md`
  - `docs/zdoc-system-autonomy-012-implementation-static-guard-scope-correction-no-runtime.md`
  - `docs/zdoc-system-autonomy-012-revalidation-static-validation-only-gate.md`
  - `docs/zdoc-system-autonomy-013-scope-and-authorization-gate.md`
  - `docs/zdoc-system-autonomy-013-implementation-static-guard-scope-correction-no-runtime.md`
  - `docs/zdoc-system-autonomy-013-revalidation-static-validation-only-gate.md`
  - `docs/zdoc-system-autonomy-014-scope-and-authorization-gate.md`
  - `docs/zdoc-system-autonomy-014-implementation-static-guard-scope-correction-no-runtime.md`
  - `docs/zdoc-system-autonomy-014-revalidation-static-validation-only-gate.md`
- 当前治理与文档治理链：
  - `docs/zdoc-system-autonomy-015-scope-and-authorization-gate.md`
  - `docs/zdoc-system-autonomy-015b-task-clarification-gate.md`
  - `docs/zdoc-system-autonomy-015c-execution-rules-gate.md`
  - `docs/zdoc-system-autonomy-015d-acceptance-and-handoff-gate.md`
  - `docs/zdoc-system-autonomy-016a-repository-baseline-inventory-gate.md`
  - `docs/zdoc-system-autonomy-016b-minimal-task-slicing-gate.md`
  - `docs/zdoc-system-autonomy-016c-readonly-acceptance-metric-gate.md`
  - `docs/zdoc-system-autonomy-016d-failsafe-and-rollback-matrix-gate.md`
  - `docs/zdoc-system-autonomy-017a-low-risk-document-governance-index-gate.md`
  - `docs/zdoc-system-autonomy-017b-document-governance-acceptance-and-archive-gate.md`

### docs 目录其他文件名级别现状

- `find docs -maxdepth 2 -type f` 显示 `docs/` 下同时存在 `LOCAL-LAUNCHER`、`KG-RUNTIME`、`MODEL-FLEET-GOVERNANCE`、`ZBID`、frontend no-write UI、Ollama advisory、trial、zdoc integration 等大量主题文件。
- 本节点仅作文件名级别观察，不打开这些主题文件内容，不判断其内容归属，不移动或重命名任何文件。
- 文件名级别可见 `custom_gpt_system_prompt.md`、`custom_gpt_actions_openapi.json`、`kg-controlled-validators/`、`kg-manifest-candidates/`、`kg-registry-candidates/`、`kg-controlled-entities/` 等路径；本节点不读取其内容，不摘要内容，不触碰真实 KG、prompt 或受保护区域。

## 文档目录规范化问题识别

本节仅从文件名、节点编号、归档顺序角度识别问题，不执行任何文件变更。

- 节点命名连续性：001 至 014 主要采用数字节点表达，015 起出现 `015`、`015b`、`015c`、`015d`、`016a`、`016b`、`016c`、`016d`、`017a`、`017b` 的字母后缀表达；从文件名级别看，存在数字节点与字母后缀节点并存。
- 015A 与 015B 等节点命名一致性：节点标题使用大写 `015A`、`015B`，文件名使用 `015`、`015b`、`015c`、`015d` 小写后缀，存在大小写与后缀表达差异。
- 文件名大小写、连字符、节点编号表达差异：早期文件名中存在 `system-autonomy-001` 作为后缀表达，后续文件名中存在 `zdoc-system-autonomy-015...` 作为前置编号表达，且 `revalidation-1` 与 `revalidation-static` 等表达并存。
- tag 名称与文件名表达差异：tag 使用 `v0.1.xxx-system-autonomy-...`，文件名使用 `docs/zdoc-system-autonomy-...md`；tag 与文件名语义一致但并非一一同形。
- docs 目录是否需要后续索引入口：当前 `docs/` 下主题文件数量较多，`SYSTEM-AUTONOMY` 文件分布在同一 docs 根目录，后续可新增索引入口文件，但必须另设节点并明确授权文件。
- 是否需要后续归档分层方案：从文件名级别看，`SYSTEM-AUTONOMY`、`LOCAL-LAUNCHER`、`KG-RUNTIME`、`MODEL-FLEET-GOVERNANCE`、`ZBID` 等主题混处于 `docs/` 下；后续可先冻结目录规范方案，再决定是否新增索引或分层归档，不得直接移动历史文件。

## 规范化目标

- 统一节点编号表达，明确数字节点、字母后缀节点和后续节点的编号规则。
- 统一文件命名风格，建立 `zdoc-system-autonomy-<node>-<topic>-gate.md` 类命名建议。
- 统一 tag 与文档关系索引，用文档索引记录节点、文件、tag、commit、归档状态之间的关系。
- 统一门控节点归档方式，区分治理规则、验收矩阵、异常阻断、文档治理、目录规范化等类别。
- 统一后续节点进入前置说明，每个节点必须重新声明仓库、分支、HEAD、tag、允许文件、禁止范围、验证命令、提交和回报格式。
- 保持历史文件不可擅自重命名；任何历史文件名、路径、tag 关系不得在本节点直接更改。
- 所有实际调整必须另设节点、另列文件清单，并在总控授权后执行。

## 后续规范化候选切片

以下仅列候选，不在本节点执行：

- `SYSTEM-AUTONOMY-018B`：文档目录规范化验收与冻结节点。
- `SYSTEM-AUTONOMY-018C`：文档目录索引文件新增候选节点。
- `SYSTEM-AUTONOMY-019A`：低风险文档目录索引执行节点。
- `LOCAL-LAUNCHER-026`：独立专线，当前禁止自动进入。

## 每个候选切片的边界

### SYSTEM-AUTONOMY-018B

- 节点名称：`SYSTEM-AUTONOMY-018B-DOCUMENT-DIRECTORY-NORMALIZATION-ACCEPTANCE-FREEZE-GATE`
- 节点目标：对 018A 的目录规范化方案进行验收与冻结，确认是否可进入后续索引新增或目录规范节点。
- 是否同一 Codex 对话框：原则上沿用当前 `/Users/youfeini/Desktop/文档生成系统` 对话框，除非总控明确要求新开。
- 是否启用目标模式：启用。
- 是否允许修改既有文件：不允许。
- 允许文件范围：仅允许新增总控明确的 018B 验收冻结文档。
- 禁止范围：禁止代码、配置、测试、prompt、runtime、endpoint、localhost、Ollama、模型推理、真实 KG、真实项目资料、secrets、output、job、export、log、青天评标仓库、`LOCAL-LAUNCHER-026`。
- 质量检查方式：仅允许文档 diff 与 git 状态检查；不得运行测试、编译、服务或模型相关命令。
- 是否可提交 tag：可在总控明确 commit message 与 tag 后提交。
- 是否自动进入下一节点：否。

### SYSTEM-AUTONOMY-018C

- 节点名称：`SYSTEM-AUTONOMY-018C-DOCUMENT-DIRECTORY-INDEX-FILE-CANDIDATE-GATE`
- 节点目标：在 018B 冻结方案后，定义是否新增目录索引文件及其授权文件清单。
- 是否同一 Codex 对话框：原则上沿用当前目标仓库对话框，除非总控明确要求新开。
- 是否启用目标模式：启用。
- 是否允许修改既有文件：默认不允许；如需修改必须由总控逐项列出。
- 允许文件范围：默认仅允许新增 1 个目录索引候选文档；具体路径必须由总控明确。
- 禁止范围：禁止未授权移动、重命名、删除或改写历史文档；禁止代码、配置、测试、prompt、runtime、endpoint、localhost、Ollama、模型推理、真实 KG、真实项目资料、secrets、output、job、export、log、青天评标仓库、`LOCAL-LAUNCHER-026`。
- 质量检查方式：仅允许总控明确的静态文档检查和 git 状态检查。
- 是否可提交 tag：可在总控明确 commit message 与 tag 后提交。
- 是否自动进入下一节点：否。

### SYSTEM-AUTONOMY-019A

- 节点名称：`SYSTEM-AUTONOMY-019A-LOW-RISK-DOCUMENT-DIRECTORY-INDEX-EXECUTION-GATE`
- 节点目标：在 018B/018C 明确并冻结后，低风险新增文档目录索引执行文件。
- 是否同一 Codex 对话框：原则上沿用当前目标仓库对话框，除非总控明确要求新开。
- 是否启用目标模式：启用。
- 是否允许修改既有文件：默认不允许；优先新增单个索引文件。
- 允许文件范围：必须由总控明确 1 个或少量文档文件；未列入清单的文件不得修改、stage、提交、移动或删除。
- 禁止范围：禁止实际目录重排、历史文件重命名、代码、配置、测试、prompt、runtime、endpoint、localhost、Ollama、模型推理、真实 KG、真实项目资料、secrets、output、job、export、log、青天评标仓库、`LOCAL-LAUNCHER-026`。
- 质量检查方式：仅允许文档 diff 与 git 状态检查，除非总控另行授权。
- 是否可提交 tag：可在总控明确 commit message 与 tag 后提交。
- 是否自动进入下一节点：否。

### LOCAL-LAUNCHER-026

- 节点名称：`LOCAL-LAUNCHER-026`
- 节点目标：独立专线处理 launcher 相关任务；目标必须由专线授权节点重新定义。
- 是否同一 Codex 对话框：不得由当前 `SYSTEM-AUTONOMY` 链条自动决定，必须由总控明确。
- 是否启用目标模式：必须由专线授权节点明确。
- 是否允许修改既有文件：当前节点不授权任何 launcher 文件变化。
- 允许文件范围：必须由专线授权节点另行定义。
- 禁止范围：当前 `SYSTEM-AUTONOMY` 链条不得进入 launcher 实现、runtime、endpoint、localhost、Ollama、模型推理或任何未授权文件。
- 质量检查方式：必须由专线授权节点另行定义。
- 是否可提交 tag：必须由专线授权节点另行定义。
- 是否自动进入下一节点：否。

## 推荐下一节点

推荐下一节点为 `SYSTEM-AUTONOMY-018B`。

推荐理由：018A 只形成目录规范化方案，018B 应对方案进行验收冻结，仍不直接改动目录结构。

任何实际目录索引新增、历史文件重命名、移动或归档分层，都必须在 018B 之后另设低风险节点，逐项明确允许文件清单、禁止范围、质量检查方式、commit message 和 tag。

## 当前受保护区域

以下区域继续受保护，不得进入、不得读取内容、不得修改：

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

## 当前不得进入事项

- 不得进入 `LOCAL-LAUNCHER-026`。
- 不得进入 `SYSTEM-AUTONOMY-018B` 或后续节点。
- 不得进入青天评标仓库。
- 不得进入 runtime / endpoint / localhost / Ollama / 模型推理。
- 不得进入 prompt / 真实 KG / 真实项目资料 / secrets。
- 不得进入 output / job / export / log。
- 不得实际重命名、移动、删除、改写任何既有文档。

## 最终收口说明

- 018A 完成后，仅形成文档目录规范化方案。
- 018A 不改变任何既有文件。
- 018A 完成后不得自动进入 `SYSTEM-AUTONOMY-018B` 或 `LOCAL-LAUNCHER-026`。

## 本节点验收标准

- 仅新增本文档 1 个授权文件。
- 不修改 015A 至 017B 既有节点文档。
- 不实际重命名、移动、删除、改写任何既有文档。
- 不修改任何代码文件、配置文件、测试文件或 prompt 文件。
- 不运行测试、编译、服务、浏览器、localhost、runtime、endpoint、Ollama 或模型推理。
- 不触碰 prompt、真实 KG、真实项目资料、secrets、output、job、export、log。
- 不进入或修改青天评标仓库。
- 不进入 `LOCAL-LAUNCHER-026`。
- 不进入 `SYSTEM-AUTONOMY-018B` 或任何后续节点。
- `git diff --check` 通过。
- `git diff --cached --check` 通过。
- 提交并创建 tag：`v0.1.692-system-autonomy-018a-document-directory-normalization-plan-gate`。
