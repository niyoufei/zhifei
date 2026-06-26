# SYSTEM-AUTONOMY-016D-FAILSAFE-AND-ROLLBACK-MATRIX-GATE

## 当前基线确认

- 仓库根路径：`/Users/youfeini/Desktop/文档生成系统`
- 当前 git root：`/Users/youfeini/Desktop/文档生成系统`
- 当前分支：`main`
- 起始 HEAD：`570ad737c003f2e6f826572a40db9214c2edd806`
- 起始 tag：`v0.1.688-system-autonomy-016c-readonly-acceptance-metric-gate`
- 上一节点名称：`SYSTEM-AUTONOMY-016C-READONLY-ACCEPTANCE-METRIC-GATE`
- 上一节点产物文件：`docs/zdoc-system-autonomy-016c-readonly-acceptance-metric-gate.md`
- 当前工作区状态：起步检查时 `git status --short` 无输出，工作区 clean。

## 016D 节点定位

- 本节点为 `SYSTEM-AUTONOMY-016D` 异常阻断与回滚前置机制矩阵门控。
- 本节点只基于 `SYSTEM-AUTONOMY-015A` 至 `SYSTEM-AUTONOMY-016C` 已形成的治理链、任务切片和验收指标矩阵，形成异常发现、立即停止、禁止自行修复、回滚前置判断、总控复核、后续恢复条件的文档化规则矩阵。
- 本节点不是功能实现节点。
- 本节点不修改任何代码、配置、测试、prompt、runtime、endpoint、localhost、Ollama、模型推理、真实 KG、真实项目资料、secrets、output、job、export 或 log。
- 本节点不进入 `SYSTEM-AUTONOMY-017A`。
- 本节点不进入 `LOCAL-LAUNCHER-026`。

## 015A 至 016C 治理链摘要

- `SYSTEM-AUTONOMY-015A`：授权范围门控。确认未发现明确实现授权，不允许直接进入 `SYSTEM-AUTONOMY` 实现，并将 `LOCAL-LAUNCHER-026` 划为 runtime / endpoint launcher 独立路线。
- `SYSTEM-AUTONOMY-015B`：任务明确化门控。固化任务边界、执行对象、禁止项和后续节点进入条件，并吸收非目标仓库 cwd 偏差。
- `SYSTEM-AUTONOMY-015C`：执行规则固化门控。固化同一 Codex 对话框、目标模式、cwd 起步确认、仓库边界、文件变更、禁止命令、异常停止和完成回报规则。
- `SYSTEM-AUTONOMY-015D`：验收闭环与交接门控。确认 015A 至 015D 均为文档门控节点，并形成后续 `SYSTEM-AUTONOMY` 节点执行前的治理基线。
- `SYSTEM-AUTONOMY-016A`：仓库基线盘点与后续任务候选映射门控。仅基于授权只读范围和文件名级盘点识别候选方向与受保护区域。
- `SYSTEM-AUTONOMY-016B`：后续任务最小切片门控。将候选方向切为低风险、单节点、单目标、单仓库、可验收、可阻断的任务切片。
- `SYSTEM-AUTONOMY-016C`：只读验收指标矩阵门控。将 cwd、git root、branch、HEAD、tag、origin/main、工作区、暂存区、文件变更、禁止行为、节点推进和回报完整性转化为可量化、可审计、可阻断、可回报的验收指标。
- 约束价值：015A 至 016C 共同规定了异常判定的证据来源、阻断阈值、回报字段和禁止自行修复边界，使 016D 可以把异常处理前置为矩阵化门控，而不是在污染发生后由 Codex 自行补救。

## 异常类型矩阵

| 异常类型 | 异常识别方式 | 判定标准 | 是否立即停止 | 是否允许自行修复 | 是否需要总控复核 | 回报字段要求 |
| --- | --- | --- | --- | --- | --- | --- |
| cwd 或 git root 错误 | `pwd`、`git rev-parse --show-toplevel` | 任一输出不是 `/Users/youfeini/Desktop/文档生成系统`。 | 是 | 否 | 是 | 当前 cwd、当前 git root、未执行后续动作确认。 |
| branch 非 main | `git branch --show-current` | 输出不是 `main`。 | 是 | 否 | 是 | 当前分支、预期分支、停止位置。 |
| HEAD 与起始 HEAD 不一致 | `git rev-parse HEAD` | 输出不是节点指定起始 HEAD。 | 是 | 否 | 是 | 实际 HEAD、预期 HEAD、tag 输出。 |
| git status 非 clean | `git status --short` | 起步状态有任意输出。 | 是 | 否 | 是 | status 原始输出、是否存在 staged 或 unstaged。 |
| 出现非授权文件变化 | `git diff --name-only`、`git status --short` | 授权文件以外任一路径出现变化。 | 是 | 否 | 是 | 非授权路径清单、授权路径清单、检查命令。 |
| 出现 staged 非授权文件 | `git diff --cached --name-only` | 暂存区出现授权文件以外路径。 | 是 | 否 | 是 | staged 路径清单、授权文件、是否已提交。 |
| 修改既有节点文档 | diff 或 staged 文件名检查 | 015A 至 016C 任一既有节点文档出现在 diff 或 staged。 | 是 | 否 | 是 | 被修改节点文档路径、diff 状态。 |
| 修改代码文件 | diff 或 staged 文件名检查 | `.py`、`.js`、`.ts`、`.tsx`、`.vue`、`.html` 等代码文件出现在变化中。 | 是 | 否 | 是 | 代码文件路径、是否 staged、是否 committed。 |
| 修改配置文件 | diff 或 staged 文件名检查 | `requirements.txt`、`pytest.ini`、`package.json`、`manifest.json`、`openapi.json` 等配置文件出现在变化中。 | 是 | 否 | 是 | 配置文件路径、变化状态。 |
| 修改 prompt 文件 | diff、staged 或操作记录检查 | prompt 文件被读取或修改。 | 是 | 否 | 是 | prompt 路径级信息，不摘要内容。 |
| 触碰 runtime / endpoint / localhost / Ollama / 模型推理 | 操作记录、命令记录、路径检查 | 启动、访问、调用或修改相关区域。 | 是 | 否 | 是 | 触碰类型、命令或路径级信息。 |
| 触碰真实 KG / 真实项目资料 / secrets | 操作记录、路径检查 | 读取内容、修改内容或摘要内容。 | 是 | 否 | 是 | 路径级信息，不回报内容。 |
| 触碰 output / job / export / log | 操作记录、路径检查 | 读取内容、生成或修改相关文件。 | 是 | 否 | 是 | 路径级信息、是否产生输出。 |
| 进入或修改青天评标仓库 | `pwd`、操作记录 | 进入 `/Users/youfeini/Desktop/ZhiFei_BizSystem` 或修改其内容。 | 是 | 否 | 是 | 当前 cwd、是否有文件变化。 |
| 自动进入 LOCAL-LAUNCHER-026 | 操作记录、文档内容检查 | 执行或准备执行 launcher 专线任务。 | 是 | 否 | 是 | 触发原因、已执行动作、停止点。 |
| 自动进入后续 SYSTEM-AUTONOMY 节点 | 操作记录、文档内容检查 | 未获授权即执行 017A 或后续节点。 | 是 | 否 | 是 | 后续节点名称、已执行动作、停止点。 |
| push rejected | push 命令输出 | `git push origin main` 或 tag push 被远端拒绝。 | 是 | 否 | 是 | push 命令、完整失败摘要、当前 HEAD、当前 tag。 |
| 远端 main 与本地预期不一致 | push 输出或已知本地 refs 状态 | push 不能把本节点提交推进到 `origin/main`。 | 是 | 否 | 是 | 本地 HEAD、预期远端指向、push 结果。 |
| tag 缺失、重复或指向错误 | `git tag --points-at HEAD`、tag push 输出 | 指定 tag 不存在、重复创建失败、或未指向本节点提交。 | 是 | 否 | 是 | tag 名称、当前 HEAD、tag 检查输出。 |

## 立即停止矩阵

| 停止触发条件 | 停止时允许执行的只读命令 | 停止时禁止执行的命令 | 停止后必须回报的信息 | 停止后不得自行进入的操作 |
| --- | --- | --- | --- | --- |
| cwd、git root、branch、HEAD、tag、工作区任一基线不匹配 | `pwd`、`git rev-parse --show-toplevel`、`git status --short`、`git rev-parse HEAD`、`git branch --show-current`、`git tag --points-at HEAD` | `git fetch`、`git pull`、`git merge`、`git rebase`、`git reset`、`git checkout`、`git clean`、`git stash` | 实际输出、预期值、停止原因。 | 不得写文件、stage、commit、tag、push。 |
| 出现非授权文件变化或 staged 污染 | `git status --short`、`git diff --name-only`、`git diff --cached --name-only` | reset、checkout、clean、stash、删除文件、临时补丁掩盖污染 | 非授权路径、是否 staged、是否 committed。 | 不得自行清理、不得继续提交。 |
| 发现禁止区域被触碰 | 仅允许记录路径级状态的只读检查，不得打开内容 | 读取内容、摘要内容、修改内容、运行服务或模型 | 路径级信息、触碰类型、停止点。 | 不得继续读取、不得生成摘要。 |
| push rejected 或远端不一致 | `git status --short`、`git rev-parse HEAD`、`git tag --points-at HEAD` | fetch、pull、merge、rebase、force push、删除 tag | push 失败摘要、本地 HEAD、tag 输出。 | 不得自行同步、不得覆盖远端。 |
| 发现需要进入后续节点或专线 | 无需额外命令；可回报当前节点状态 | 任何 017A、017B、LOCAL-LAUNCHER-026、runtime、endpoint、模型相关命令 | 触发的后续方向、当前节点完成状态。 | 不得自动进入下一节点。 |

## 禁止自行修复矩阵

| 禁止修复行为 | 禁止原因 | 违规判定 | 正确处置 |
| --- | --- | --- | --- |
| 禁止 reset | reset 会改写当前工作状态，掩盖污染来源。 | 执行 `git reset`。 | 停止并回报，由总控决定清理指令。 |
| 禁止 checkout | checkout 可能丢弃或替换文件状态。 | 执行 `git checkout`。 | 停止并回报实际状态。 |
| 禁止 clean | clean 会删除未跟踪证据。 | 执行 `git clean`。 | 保留现场并回报 untracked 路径。 |
| 禁止 stash | stash 会隐藏异常状态。 | 执行 `git stash`。 | 回报当前 status，不隐藏改动。 |
| 禁止删除 tag | 删除 tag 会破坏 tag 污染证据链。 | 删除本地或远端 tag。 | 停止并等待总控复核。 |
| 禁止覆盖远端 | 覆盖远端会扩大事故影响。 | force push 或等价覆盖行为。 | 停止并回报 push 状态。 |
| 禁止重新提交覆盖问题 | 新 commit 可能把污染包装成正常变更。 | 为掩盖异常而追加、amend 或替换提交。 | 保留当前提交状态并回报。 |
| 禁止自行修改非授权文件 | 会扩大节点允许范围。 | 修改、删除、移动或 stage 非授权路径。 | 停止并回报路径清单。 |
| 禁止通过临时补丁掩盖污染 | 临时补丁会制造二次状态。 | 生成或应用补丁以绕过异常。 | 停止，等待总控明确补救节点。 |
| 禁止把异常状态继续推进到下一节点 | 异常未审计前进入下一节点会污染治理链。 | 在异常未清楚时执行后续节点。 | 停止并触发事故审计判断。 |

## 回滚前置判断矩阵

回滚不是本节点可执行动作。本节点只形成回滚前置判断标准，不执行 reset、checkout、clean、stash、tag 删除、远端覆盖或任何自动回滚。

| 回滚前置事项 | 可判定依据 | 只读检查方式 | 是否允许自动回滚 | 下一步处理原则 |
| --- | --- | --- | --- | --- |
| 是否存在 commit 污染 | 非授权文件被提交或 commit message 不符。 | `git log --oneline --decorate -n 20`、`git status --short` | 否 | 另起事故审计节点，由总控决定是否 revert 或其他处置。 |
| 是否存在 tag 污染 | tag 缺失、重复、命名错误或指向错误。 | `git tag --points-at HEAD` | 否 | 保留 tag 状态，等待总控生成 tag 清理指令。 |
| 是否存在远端 main 污染 | push 后远端 main 指向非预期提交。 | push 输出与本地最终 HEAD 对照。 | 否 | 停止并请求总控复核远端修复方式。 |
| 是否存在远端 tag 污染 | 远端 tag 已推送但指向错误或名称错误。 | tag push 输出与本地 tag 对照。 | 否 | 停止并等待总控决定远端 tag 处理。 |
| 是否仅存在本地未提交污染 | `git status --short` 有 unstaged 或 untracked 非授权路径。 | `git status --short`、`git diff --name-only` | 否 | 回报路径，不自行删除或 checkout。 |
| 是否仅存在 staged 污染 | 暂存区有非授权路径但尚未提交。 | `git diff --cached --name-only` | 否 | 回报 staged 路径，不自行 unstage。 |
| 是否存在非授权文件改动 | 授权清单之外出现变化。 | `git diff --name-only`、`git diff --cached --name-only` | 否 | 触发停止，等待总控复核。 |
| 是否存在跨仓库污染 | 操作发生在青天评标仓库或其他非目标仓库。 | `pwd`、`git rev-parse --show-toplevel` | 否 | 停止并回报仓库路径。 |
| 是否需要另起事故审计节点 | 存在提交、tag、远端、跨仓库或禁止区域污染。 | 汇总只读检查结果。 | 否 | 由总控单独下发事故审计节点。 |
| 是否需要总控生成清理指令 | 任一污染需要修改、删除、回滚或远端处理。 | 对照异常类型矩阵。 | 否 | Codex 不生成隐式清理动作，只等待明确授权。 |

## 恢复执行条件矩阵

| 恢复条件 | 合格标准 | 检查方式 | 未满足时处理 |
| --- | --- | --- | --- |
| 仓库根路径确认 | 当前路径必须为 `/Users/youfeini/Desktop/文档生成系统`。 | `pwd` | 停止并回报。 |
| 分支确认 | 当前分支必须为总控指定分支，默认 `main`。 | `git branch --show-current` | 停止并回报。 |
| HEAD 确认 | 当前 HEAD 必须等于恢复指令指定 HEAD。 | `git rev-parse HEAD` | 停止并回报。 |
| tag 确认 | 当前 HEAD 必须具备恢复指令指定 tag。 | `git tag --points-at HEAD` | 停止并回报。 |
| 工作区 clean | `git status --short` 必须无输出。 | `git status --short` | 停止并回报 status。 |
| 暂存区 clean | `git diff --cached --name-only` 必须无输出。 | `git diff --cached --name-only` | 停止并回报 staged 路径。 |
| 授权文件清单重新确认 | 恢复指令必须重新列出允许新增或修改文件。 | 对照用户指令。 | 缺失则不得恢复。 |
| 禁止范围重新确认 | 恢复指令必须重新列出禁止区域与禁止命令。 | 对照用户指令。 | 缺失则不得恢复。 |
| 是否新开 Codex 对话框确认 | 恢复指令必须明确是否沿用当前对话框。 | 对照用户指令。 | 缺失则等待确认。 |
| 是否启用目标模式确认 | 恢复指令必须明确是否启用目标模式。 | 对照用户指令。 | 缺失则等待确认。 |
| 是否允许恢复当前节点 | 总控必须明确恢复的是当前节点还是新事故审计节点。 | 对照用户指令。 | 缺失则不得继续。 |
| 是否必须重新下发完整指令 | 发生污染、远端不一致、tag 异常、跨仓库异常时，必须重新下发完整指令。 | 对照异常类型矩阵。 | 等待完整指令。 |

## 事故审计触发规则

以下任一情况出现时，应触发事故审计判断；本节点只记录触发标准，不自动执行事故审计：

- 疑似错仓库执行：cwd 或 git root 不是 `/Users/youfeini/Desktop/文档生成系统`。
- 疑似错误 HEAD 执行：当前 HEAD 与节点起始 HEAD 或恢复指令指定 HEAD 不一致。
- 疑似非授权文件修改：授权清单之外出现 tracked、untracked、staged 或 committed 变化。
- 疑似远端污染：push rejected、远端 main 指向非预期提交、或本地无法证明远端状态符合预期。
- 疑似 tag 污染：tag 缺失、重复、命名错误、指向错误或远端 tag push 异常。
- 疑似跨专线执行：当前 `SYSTEM-AUTONOMY` 链条中进入 `LOCAL-LAUNCHER-026`、青天评标仓库或其他专线。
- 疑似模型、runtime、localhost 被触碰：出现启动服务、浏览器、localhost、runtime、endpoint、Ollama、模型推理相关动作。
- 用户截图或 Codex 回报出现不一致：界面显示仓库、分支、HEAD、tag、status 与命令输出不一致。
- Codex 指令不完整或缺少审计结构：缺少起始 HEAD、tag、允许文件、禁止范围、停止条件、提交和回报格式。

## 后续节点候选

以下仅列候选，不在本节点执行：

- `SYSTEM-AUTONOMY-017A`：首个低风险文档治理执行节点。
- `SYSTEM-AUTONOMY-017B`：文档治理验收与归档节点。
- `LOCAL-LAUNCHER-026`：独立专线，当前禁止自动进入。

## 推荐下一节点

推荐下一节点为 `SYSTEM-AUTONOMY-017A`。

推荐理由：015A 至 016D 已完成治理、切片、验收与异常阻断矩阵，后续可进入首个低风险文档治理执行节点。

`SYSTEM-AUTONOMY-017A` 必须继续保持低风险、单文件、文档类、可回滚前置判断，不得进入代码实现，不得进入配置、测试、prompt、runtime、endpoint、localhost、Ollama、模型推理、真实 KG、真实项目资料、secrets、output、job、export、log 或青天评标仓库。

## 当前不得进入事项

- 不得进入 `LOCAL-LAUNCHER-026`。
- 不得进入 `SYSTEM-AUTONOMY-017A` 或后续节点。
- 不得进入青天评标仓库。
- 不得进入 runtime / endpoint / localhost / Ollama / 模型推理。
- 不得进入 prompt / 真实 KG / 真实项目资料 / secrets。
- 不得进入 output / job / export / log。

## 最终收口说明

- `SYSTEM-AUTONOMY-016D` 完成后，`SYSTEM-AUTONOMY` 已具备从授权、任务、执行、验收、盘点、切片、指标、异常阻断到回滚前置判断的完整治理闭环。
- `SYSTEM-AUTONOMY-016D` 完成后仍不得自动进入 `SYSTEM-AUTONOMY-017A` 或 `LOCAL-LAUNCHER-026`。
- 下一步仅由总控基于本节点回报结果继续决策。

## 本节点验收标准

- 仅新增本文档 1 个授权文件。
- 不修改 015A 至 016C 既有节点文档。
- 不修改任何代码文件、配置文件、测试文件或 prompt 文件。
- 不运行测试、编译、服务、浏览器、localhost、runtime、endpoint、Ollama 或模型推理。
- 不触碰 prompt、真实 KG、真实项目资料、secrets、output、job、export、log。
- 不进入或修改青天评标仓库。
- 不进入 `LOCAL-LAUNCHER-026`。
- 不进入 `SYSTEM-AUTONOMY-017A` 或任何后续节点。
- `git diff --check` 通过。
- `git diff --cached --check` 通过。
- 提交并创建 tag：`v0.1.689-system-autonomy-016d-failsafe-rollback-matrix-gate`。
