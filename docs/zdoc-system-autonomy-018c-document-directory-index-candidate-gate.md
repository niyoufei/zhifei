# SYSTEM-AUTONOMY-018C-DOCUMENT-DIRECTORY-INDEX-CANDIDATE-GATE

## 当前基线确认

- 仓库根路径：`/Users/youfeini/Desktop/文档生成系统`
- 当前 git root：`/Users/youfeini/Desktop/文档生成系统`
- 当前分支：`main`
- 起始 HEAD：`f67c472a7e5fe663288ee0b35f93b32fb3af14a8`
- 起始 tag：`v0.1.693-system-autonomy-018b-document-directory-normalization-freeze-gate`
- 上一节点名称：`SYSTEM-AUTONOMY-018B-DOCUMENT-DIRECTORY-NORMALIZATION-FREEZE-GATE`
- 上一节点产物文件：`docs/zdoc-system-autonomy-018b-document-directory-normalization-freeze-gate.md`
- 当前工作区状态：起步检查时 `git status --short` 无输出，工作区 clean。

## 018C 节点定位

- 本节点为“文档目录索引文件候选方案门控”。
- 本节点只形成后续正式文档目录索引文件的候选方案，不创建正式目录索引文件。
- 本节点不是功能实现节点。
- 本节点不修改任何代码、配置、测试、prompt、runtime、endpoint、localhost、Ollama、模型推理、真实 KG、真实项目资料、secrets、output、job、export 或 log。
- 本节点不重命名、移动、删除或改写任何既有文档。
- 本节点不进入 `SYSTEM-AUTONOMY-019A` 或任何后续节点。
- 本节点不进入 `LOCAL-LAUNCHER-026`。

## 018A 至 018B 冻结结论承接

- `SYSTEM-AUTONOMY-018A` 已形成文档目录规范化方案，识别了 docs 目录中文档索引、节点编号、文件命名、tag 关系和后续目录治理的候选切片。
- `SYSTEM-AUTONOMY-018B` 已完成对 018A 方案的验收与冻结，明确 018A 和 018B 均不授权实际目录调整。
- `SYSTEM-AUTONOMY-018C` 只能基于 018A 的方案和 018B 的冻结结论，提出后续目录索引文件的候选定位、命名、字段、内容边界、风险控制和执行前置条件。
- `SYSTEM-AUTONOMY-018C` 不构成正式索引文件创建授权。
- 任何正式索引文件新增必须另设节点，并由总控明确文件名、字段范围、允许新增文件清单、禁止范围、验证命令、commit message 和 tag。

## 目录索引文件候选定位

- 候选索引文件的作用：为已完成的 `SYSTEM-AUTONOMY` 节点提供查阅入口，记录节点编号、节点名称、产物文件、commit、tag、完成状态、治理边界和后续约束。
- 候选索引文件与现有 `docs/zdoc-system-autonomy-*` 节点文档的关系：索引文件只引用和定位已完成节点，不替代任何节点文档，也不改变节点文档的原始结论。
- 候选索引文件不替代既有节点文档：每个节点的权威内容仍以对应 `docs/zdoc-system-autonomy-*` 文档和完成 tag 为准。
- 候选索引文件不得改写历史节点内容：不得修订、压缩、重写、删除或重新解释历史节点正文。
- 候选索引文件应作为后续查阅入口和治理链路目录：它只提供可审计导航，不承担新的授权、实现或验收职责。

## 候选索引文件命名方案

| 方案 | 文件名 | 适用场景 | 优点 | 风险 | 是否推荐 | 是否允许在本节点执行 |
| --- | --- | --- | --- | --- | --- | --- |
| 方案 A | `docs/zdoc-system-autonomy-index.md` | 需要为 `SYSTEM-AUTONOMY` 全链路提供一个简短、稳定、入口型索引。 | 文件名短，入口明确，便于后续查阅和引用。 | 名称较宽，未来若索引范围扩展，必须严格限定只记录 `SYSTEM-AUTONOMY` 已完成节点事实。 | 推荐，优先级 1。 | 否，本节点只做候选方案。 |
| 方案 B | `docs/zdoc-system-autonomy-directory-index.md` | 需要强调索引用途是 docs 目录治理和目录关系，而不是一般治理总览。 | 语义更具体，更贴近 018A 至 018C 的目录规范化链路。 | 文件名较长，后续引用成本略高。 | 可选，优先级 2。 | 否，本节点只做候选方案。 |
| 方案 C | 不新增索引文件，仅在后续节点文档中引用既有节点链 | 当前认为新增正式索引文件收益不足，或总控希望继续保持单节点文档链式查阅。 | 零新增正式索引文件，不引入新维护面。 | 查阅入口分散，tag、commit、节点文档关系仍需在多个节点中追溯。 | 不推荐，优先级 3。 | 否，本节点不执行后续策略。 |

候选结论：若后续进入正式执行节点，优先采用方案 A；若总控更重视目录治理语义，可采用方案 B；方案 C 仅作为不新增索引文件的保守备选。

## 候选索引字段设计

以下仅为字段设计，不创建索引文件：

| 字段 | 字段含义 | 记录边界 |
| --- | --- | --- |
| 节点编号 | 例如 `015A`、`018B`、`019A`。 | 仅记录已完成或总控明确允许列入的节点编号。 |
| 节点名称 | 节点完整大写名称。 | 不改写节点原文标题。 |
| 节点类型 | 例如授权门控、验收门控、冻结门控、候选方案门控、执行门控。 | 基于节点文档事实归类，不新增隐式授权。 |
| 产物文件 | 对应 `docs/zdoc-system-autonomy-*.md` 文件路径。 | 只记录仓库内已存在或后续节点新增的授权文件。 |
| commit hash | 节点完成提交。 | 以 git 历史中完成节点的提交为准。 |
| tag | 节点完成 tag。 | 不移动、不删除、不重指 tag。 |
| 完成状态 | 已完成、已冻结、已归档或候选。 | 不把未完成节点标为完成。 |
| 是否文档节点 | 表示该节点是否只产出文档。 | 基于节点验收和实际 diff 判断。 |
| 是否功能实现节点 | 表示该节点是否涉及功能实现。 | 仅按事实记录，不推断未确认内容。 |
| 是否触碰代码 | 表示该节点是否修改代码文件。 | 以提交文件清单和节点验收为依据。 |
| 是否触碰受保护区域 | 表示是否触碰 runtime、endpoint、prompt、真实数据等区域。 | 未经证据不得标记为已触碰或未触碰之外的结论。 |
| 后续约束作用 | 记录该节点对后续任务的边界约束。 | 只摘要约束类别，不替代节点原文。 |
| 下一节点建议 | 记录该节点给出的推荐后续节点。 | 只作为历史建议，不自动进入下一节点。 |

## 索引文件内容边界

- 只记录已完成节点事实。
- 不得重写历史结论。
- 不得覆盖节点原文。
- 不得修改 tag。
- 不得修改 commit 历史。
- 不得引用未确认内容。
- 不得进入真实 KG、真实项目资料、secrets、prompt、output、job、export 或 log。
- 不得引用青天评标仓库内部内容。
- 不得把候选方案、未来计划或推荐下一节点写成已完成事实。
- 不得通过索引文件授予代码、runtime、endpoint、localhost、Ollama、模型推理或其他受保护区域的执行权限。

## 后续执行前置条件

若后续要真正新增目录索引文件，必须同时满足以下条件：

- `SYSTEM-AUTONOMY-018C` 已完成并提交。
- `v0.1.694-system-autonomy-018c-document-directory-index-candidate-gate` 已创建并推送。
- `origin/main` 已指向 `SYSTEM-AUTONOMY-018C` 完成后的 HEAD。
- 工作区 clean。
- 暂存区 clean。
- 015A 至 018B 既有节点文档未被修改。
- 未实际重命名、移动、删除或改写任何既有文档。
- 明确正式索引文件名。
- 明确正式索引文件内容字段。
- 明确只新增 1 个索引文件，或明确完整文件清单。
- 明确不得进入代码、runtime、prompt、真实数据、output 或 log。
- 当前 Codex 对话框仍对应 `/Users/youfeini/Desktop/文档生成系统` 仓库。
- 后续节点必须重新声明允许读取、允许新增、允许修改、允许移动、允许删除的路径白名单。
- 后续节点必须重新声明禁止命令、质量检查、commit message、tag 和完成回报格式。

## 后续任务候选

以下仅列候选，不在本节点执行：

- `SYSTEM-AUTONOMY-019A`：低风险文档目录索引执行节点。
- `SYSTEM-AUTONOMY-019B`：目录索引验收归档节点。
- `LOCAL-LAUNCHER-026`：独立专线，当前禁止自动进入。

## 推荐下一节点

从总控角度，推荐下一节点为 `SYSTEM-AUTONOMY-019A`。

推荐理由：018A 已完成文档目录规范化方案，018B 已完成方案验收与冻结，018C 完成候选索引设计后，可以进入“只新增正式目录索引文件”的低风险执行节点。

`SYSTEM-AUTONOMY-019A` 必须继续保持低风险、文档类、单文件、单目标，不得重命名、移动、删除或改写既有文件，不得进入代码实现、runtime、endpoint、localhost、Ollama、模型推理、prompt、真实 KG、真实项目资料、secrets、output、job、export、log、青天评标仓库或 `LOCAL-LAUNCHER-026`。

## 当前受保护区域

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
- 青天评标仓库
- `LOCAL-LAUNCHER-026`

## 当前不得进入事项

- 不得进入 `LOCAL-LAUNCHER-026`。
- 不得进入 `SYSTEM-AUTONOMY-019A` 或任何后续节点。
- 不得进入青天评标仓库。
- 不得进入 runtime / endpoint / localhost / Ollama / 模型推理。
- 不得进入 prompt / 真实 KG / 真实项目资料 / secrets。
- 不得进入 output / job / export / log。
- 不得创建正式目录索引文件。
- 不得实际重命名、移动、删除或改写任何既有文档。

## 最终收口说明

- `SYSTEM-AUTONOMY-018C` 完成后，仅形成文档目录索引文件候选方案。
- `SYSTEM-AUTONOMY-018C` 不改变任何既有文件。
- `SYSTEM-AUTONOMY-018C` 不创建正式目录索引文件。
- `SYSTEM-AUTONOMY-018C` 完成后不得自动进入 `SYSTEM-AUTONOMY-019A` 或 `LOCAL-LAUNCHER-026`。

## 本节点验收标准

- 仅新增本文档 1 个授权文件。
- 不修改 015A 至 018B 既有节点文档。
- 不创建正式目录索引文件。
- 不实际重命名、移动、删除或改写任何既有文档。
- 不修改任何代码文件、配置文件、测试文件或 prompt 文件。
- 不运行测试、编译、服务、浏览器、localhost、runtime、endpoint、Ollama 或模型推理。
- 不触碰 prompt、真实 KG、真实项目资料、secrets、output、job、export、log。
- 不进入或修改青天评标仓库。
- 不进入 `LOCAL-LAUNCHER-026`。
- 不进入 `SYSTEM-AUTONOMY-019A` 或任何后续节点。
- `git diff --check` 通过。
- `git diff --cached --check` 通过。
- 提交并创建 tag：`v0.1.694-system-autonomy-018c-document-directory-index-candidate-gate`。
