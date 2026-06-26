# SYSTEM-AUTONOMY-016C-READONLY-ACCEPTANCE-METRIC-GATE

## 当前基线确认

- 仓库根路径：`/Users/youfeini/Desktop/文档生成系统`
- 当前分支：`main`
- 起始 HEAD：`64deae6ea7ec303731a5c0545e154f2058188312`
- 起始 tag：`v0.1.687-system-autonomy-016b-minimal-task-slicing-gate`
- 上一节点名称：`SYSTEM-AUTONOMY-016B-MINIMAL-TASK-SLICING-GATE`
- 上一节点产物文件：`docs/zdoc-system-autonomy-016b-minimal-task-slicing-gate.md`
- 当前工作区状态：起步检查时 `git status --short` 无输出，工作区 clean。

## 016C 节点定位

- 本节点为 `SYSTEM-AUTONOMY-016C` 只读验收指标矩阵门控。
- 本节点只基于 `SYSTEM-AUTONOMY-015A` 至 `SYSTEM-AUTONOMY-016B` 已完成治理链形成可量化、可审计、可阻断、可回报的验收指标矩阵。
- 本节点不是功能实现节点。
- 本节点不修改任何代码、配置、测试、prompt、runtime、endpoint、localhost、Ollama、模型推理、真实 KG、真实项目资料、secrets、output、job、export 或 log。
- 本节点不进入 `SYSTEM-AUTONOMY-016D`。
- 本节点不进入 `LOCAL-LAUNCHER-026`。

## 015A 至 016B 已完成链路摘要

- `SYSTEM-AUTONOMY-015A`：授权范围门控。确认未发现明确的 015 实现任务，不授权直接进入实现，并将 `LOCAL-LAUNCHER-026` 及后续线索划为另一条 runtime / endpoint launcher 路线。
- `SYSTEM-AUTONOMY-015B`：任务明确化门控。固化后续任务边界、执行对象、禁止项和进入条件，并吸收 015A 中首次读取附件时 cwd 位于非目标仓库的偏差。
- `SYSTEM-AUTONOMY-015C`：执行规则固化门控。固化 Codex 对话框连续性、目标模式、cwd 起步确认、仓库边界、文件变更、禁止命令、异常停止和完成回报规则。
- `SYSTEM-AUTONOMY-015D`：验收闭环与交接门控。确认 015A 至 015D 均为文档门控节点，形成后续 `SYSTEM-AUTONOMY` 节点执行前的治理基线。
- `SYSTEM-AUTONOMY-016A`：仓库基线盘点与后续任务候选映射门控。基于允许的文件名级盘点和 015A 至 015D 文档，识别后续候选方向和受保护区域。
- `SYSTEM-AUTONOMY-016B`：后续任务最小切片门控。将后续方向拆分为低风险、单节点、单目标、单仓库、可验收、可阻断的候选任务切片，并推荐先进入 016C。
- 治理链价值：015A 至 016B 共同形成了从授权边界、任务澄清、执行纪律、验收交接、仓库盘点到最小切片的连续治理链，使后续节点在进入任何实现前都有明确的允许范围、禁止范围、阻断规则和回报证据。

## 约束一致性验收矩阵

| 验收对象 | 合格标准 | 检查命令或检查方式 | 不合格处理 | 是否允许继续下一节点 |
| --- | --- | --- | --- | --- |
| cwd 一致性 | `pwd` 必须等于 `/Users/youfeini/Desktop/文档生成系统`。 | `pwd` | 立即停止并回报当前路径，不得读取、写入或 git 操作。 | 否 |
| git root 一致性 | `git rev-parse --show-toplevel` 必须等于目标仓库根路径。 | `git rev-parse --show-toplevel` | 立即停止并回报 git root，不得继续。 | 否 |
| branch 一致性 | 当前分支必须为 `main`。 | `git branch --show-current` | 立即停止并回报当前分支。 | 否 |
| HEAD 连续性 | 起步 HEAD 必须等于节点指定起始 HEAD。 | `git rev-parse HEAD` | 立即停止并回报实际 HEAD。 | 否 |
| tag 连续性 | 起步 HEAD 必须指向节点指定起始 tag。 | `git tag --points-at HEAD` | 立即停止并回报当前 tag 输出。 | 否 |
| origin/main 指向一致性 | 远端 main 最终应指向本节点提交；不得通过 fetch、pull、rebase 等方式修正。 | 仅在允许的 push 成功后，以本地提交 hash 和 push 结果作为回报依据。 | push rejected 或远端不一致时立即停止，等待总控复核。 | 否 |
| 工作区 clean 状态 | 起步检查时 `git status --short` 必须无输出；完成后也应无输出。 | `git status --short` | 起步非 clean 立即停止；完成后非 clean 必须回报差异。 | 否 |
| 暂存区 clean 状态 | 提交后 `git diff --cached --name-only` 必须无输出。 | `git diff --cached --name-only` | 若仍有 staged 文件，立即停止并回报文件名。 | 否 |

## 文件变更约束验收矩阵

| 验收项 | 合格标准 | 违规判定 | 阻断规则 | 回报要求 |
| --- | --- | --- | --- | --- |
| 单节点允许文件数量 | 本节点仅允许新增 1 个文档文件。 | 出现 2 个及以上新增、修改、删除、移动文件。 | 立即停止，不得自行扩展范围。 | 回报实际变更文件清单。 |
| 授权文件清单 | 仅允许新增 `docs/zdoc-system-autonomy-016c-readonly-acceptance-metric-gate.md`。 | 任何其他路径出现在 diff、staged 或提交中。 | 立即停止，等待总控复核。 | 回报授权文件与非授权文件对比。 |
| 非授权文件变化 | 除授权文档外无 tracked 或 staged 变化。 | `git diff --name-only` 或 `git diff --cached --name-only` 出现非授权路径。 | 立即停止，不得提交。 | 回报非授权路径。 |
| 代码文件变化 | 代码文件必须零变化。 | `.py`、`.js`、`.ts`、`.tsx`、`.vue`、`.html` 等代码路径出现在 diff。 | 立即停止。 | 回报是否未修改任何代码文件。 |
| 配置文件变化 | 配置文件必须零变化。 | `requirements.txt`、`pytest.ini`、`package.json`、`manifest.json`、`openapi.json` 等配置路径出现在 diff。 | 立即停止。 | 回报是否未修改配置文件。 |
| prompt 文件变化 | prompt 文件必须零变化，且不得读取其内容。 | prompt 路径出现在 diff，或需要读取 prompt 内容。 | 立即停止。 | 回报是否未触碰 prompt。 |
| runtime / endpoint / localhost / Ollama / 模型推理相关文件变化 | 相关区域必须零变化，且不得启动或调用。 | 相关路径出现在 diff，或出现启动、访问、调用需求。 | 立即停止。 | 回报是否未触碰相关区域。 |
| output / job / export / log 变化 | 相关区域必须零变化，且不得读取内容。 | 相关路径出现在 diff，或出现生成缓存、日志、输出物。 | 立即停止。 | 回报是否未触碰 output / job / export / log。 |
| staged 文件变化 | staged 文件只能是授权文档，提交后 staged 必须为空。 | staged 出现非授权文件，或提交后 staged 未清空。 | 提交前立即停止；提交后回报异常。 | 回报 `git diff --cached --name-only` 是否为空。 |

## 禁止行为验收矩阵

| 禁止行为 | 是否允许 | 违规后处置 | 是否需要停止 | 是否需要总控复核 |
| --- | --- | --- | --- | --- |
| `git fetch` / `git pull` / `git merge` / `git rebase` / `git reset` / `git checkout` / `git clean` / `git stash` | 不允许 | 立即记录并停止，不得继续修正。 | 是 | 是 |
| `pytest` / `py_compile` / `npm run` / `pnpm` / `yarn` | 不允许 | 立即停止并回报已执行命令。 | 是 | 是 |
| 启动服务 | 不允许 | 立即停止，保留当前状态。 | 是 | 是 |
| 访问 localhost | 不允许 | 立即停止并回报访问行为。 | 是 | 是 |
| 调用 runtime / endpoint / Ollama / 模型推理 | 不允许 | 立即停止，不得继续调用。 | 是 | 是 |
| 读取或修改 prompt | 不允许 | 立即停止并回报路径级信息。 | 是 | 是 |
| 读取或修改真实 KG / 真实项目资料 / secrets | 不允许 | 立即停止，不得摘要内容。 | 是 | 是 |
| 读取或修改 output / job / export / log | 不允许 | 立即停止并回报路径级信息。 | 是 | 是 |
| 进入或修改青天评标仓库 | 不允许 | 立即停止并回报当前 cwd。 | 是 | 是 |
| 自动进入 `LOCAL-LAUNCHER-026` | 不允许 | 立即停止，等待独立专线授权。 | 是 | 是 |

## 节点推进验收矩阵

| 验收项 | 合格标准 | 检查方式 | 不合格处理 | 是否允许继续下一节点 |
| --- | --- | --- | --- | --- |
| 节点名称唯一性 | 当前只执行 `SYSTEM-AUTONOMY-016C-READONLY-ACCEPTANCE-METRIC-GATE`。 | 对照用户节点指令和新增文档标题。 | 停止并回报命名冲突。 | 否 |
| 节点目标唯一性 | 当前目标仅为只读验收指标矩阵门控。 | 对照文档内容是否出现实现、测试、runtime 或 launcher 执行。 | 停止并删去未授权目标前不得继续。 | 否 |
| 是否新开 Codex 对话框 | 当前继续使用同一 Codex 对话框。 | 执行过程自查。 | 若新建、派生、委派或并行启动其他 Codex 对话框，立即停止。 | 否 |
| 是否启用目标模式 | 当前按目标模式只执行本节点。 | 对照任务执行范围。 | 若目标模式不可用或切换失败，应回报并停止扩展。 | 否 |
| 起步检查完整性 | 必须完成 `pwd`、git root、status、HEAD、branch、tag 检查。 | 对照起步检查输出。 | 缺任一项即停止并补充回报，不得写入。 | 否 |
| 完成回报完整性 | 必须覆盖指定 40 项完成回报。 | 对照完成后回报清单。 | 缺项时停止补充回报，不进入下一节点。 | 否 |
| commit message 规范 | `docs: add system autonomy 016C readonly acceptance metric gate`。 | `git log --oneline --decorate -n 20` 或提交输出。 | message 不符时停止并等待总控，不得 reset 或 amend。 | 否 |
| tag 规范 | `v0.1.688-system-autonomy-016c-readonly-acceptance-metric-gate`。 | `git tag --points-at HEAD`。 | tag 不符时停止并等待总控，不得删除或重建 tag。 | 否 |
| push 结果 | `git push origin main` 与 tag push 均应成功。 | push 命令输出。 | push rejected 或失败立即停止。 | 否 |
| 是否自动进入下一节点 | 完成后不得进入 016D、017A 或 LOCAL-LAUNCHER-026。 | 执行过程自查。 | 发现进入下一节点需求时立即停止。 | 否 |

## 回报完整性验收矩阵

| 回报项 | 合格标准 | 证据来源 | 缺失处理 |
| --- | --- | --- | --- |
| 是否完成 | 明确回答完成或未完成。 | 任务执行结果。 | 补充回报。 |
| 当前仓库根路径 | 回报 `/Users/youfeini/Desktop/文档生成系统`。 | `pwd`。 | 补充回报。 |
| 当前分支 | 回报 `main`。 | `git branch --show-current`。 | 补充回报。 |
| 开始前 HEAD | 回报 `64deae6ea7ec303731a5c0545e154f2058188312`。 | 起步检查。 | 补充回报。 |
| 结束后 HEAD | 回报本节点 commit hash。 | `git rev-parse HEAD`。 | 补充回报。 |
| 新增或修改文件清单 | 仅列授权文档。 | `git diff --name-only`、提交内容。 | 若出现非授权文件，停止。 |
| 是否仅变更授权文件 | 必须为是。 | diff 与 staged 检查。 | 若不是，停止。 |
| `git diff --check` | 必须通过。 | 命令输出。 | 失败则停止。 |
| `git diff --cached --check` | 必须通过。 | 命令输出。 | 失败则停止。 |
| commit hash | 回报最终提交 hash。 | commit 输出或 `git rev-parse HEAD`。 | 补充回报。 |
| tag | 回报指定 tag 是否创建。 | `git tag --points-at HEAD`。 | 补充回报。 |
| origin/main 指向 | 回报成功 push 后对应提交。 | push 结果与本地最终 HEAD。 | push 失败则停止。 |
| 远端 tag 指向 | 回报成功 tag push 后对应提交。 | tag push 结果与本地 tag。 | push 失败则停止。 |
| `git status --short` | 完成后必须 clean。 | `git status --short`。 | 非 clean 则停止并回报。 |
| 是否触碰禁止区域 | 必须明确未触碰。 | 执行过程记录。 | 补充回报。 |
| 下一步建议 | 推荐 016D，但不得执行。 | 本文档后续节点候选。 | 补充回报。 |

## 后续节点候选

以下仅列候选，不在本节点执行：

- `SYSTEM-AUTONOMY-016D`：异常阻断与回滚机制矩阵门控。
- `SYSTEM-AUTONOMY-017A`：首个低风险文档治理执行节点。
- `LOCAL-LAUNCHER-026`：独立专线，当前禁止自动进入。

## 推荐下一节点

推荐下一节点为 `SYSTEM-AUTONOMY-016D`。

推荐理由：016C 形成验收指标矩阵后，需要继续形成异常阻断与回滚机制矩阵，才能闭合自治执行风险控制链。

## 当前不得进入事项

- 不得进入 `LOCAL-LAUNCHER-026`。
- 不得进入 `SYSTEM-AUTONOMY-016D` 或后续节点。
- 不得进入青天评标仓库。
- 不得进入 runtime / endpoint / localhost / Ollama / 模型推理。
- 不得进入 prompt / 真实 KG / 真实项目资料 / secrets。
- 不得进入 output / job / export / log。

## 异常阻断规则

- 当前 pwd 或 git root 不是目标仓库，立即停止。
- 当前分支不是 `main`，立即停止。
- 当前 HEAD 不等于起始 HEAD，立即停止。
- `git status --short` 非 clean，立即停止。
- 出现非授权文件变化，立即停止。
- 需要 fetch、pull、merge、rebase、reset、checkout、clean、stash 时，立即停止。
- push rejected 或远端不一致，立即停止。
- 发现需要进入 `LOCAL-LAUNCHER-026`、`SYSTEM-AUTONOMY-016D` 或其他后续节点，立即停止。

## 本节点验收标准

- 仅新增本文档 1 个授权文件。
- 不修改 015A 至 016B 既有节点文档。
- 不修改任何代码文件、配置文件、测试文件或 prompt 文件。
- 不运行测试、编译、服务、浏览器、localhost、runtime、endpoint、Ollama 或模型推理。
- 不触碰 prompt、真实 KG、真实项目资料、secrets、output、job、export、log。
- 不进入或修改青天评标仓库。
- 不进入 `LOCAL-LAUNCHER-026`。
- 不进入 `SYSTEM-AUTONOMY-016D` 或任何后续节点。
- `git diff --check` 通过。
- `git diff --cached --check` 通过。
- 提交并创建 tag：`v0.1.688-system-autonomy-016c-readonly-acceptance-metric-gate`。
