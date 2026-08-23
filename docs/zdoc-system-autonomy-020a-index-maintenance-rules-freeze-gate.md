# SYSTEM-AUTONOMY-020A-INDEX-MAINTENANCE-RULES-FREEZE-GATE

## 当前基线确认

- 仓库根路径：`/Users/youfeini/Desktop/文档生成系统`
- 当前 git root：`/Users/youfeini/Desktop/文档生成系统`
- 当前分支：`main`
- 起始 HEAD：`3ab130a312e5da8965f45a3575f17e71f62c55bf`
- 起始 tag：`v0.1.696-system-autonomy-019b-document-directory-index-acceptance-archive-gate`
- 上一节点名称：`SYSTEM-AUTONOMY-019B-DOCUMENT-DIRECTORY-INDEX-ACCEPTANCE-ARCHIVE-GATE`
- 上一节点产物文件：`docs/zdoc-system-autonomy-019b-document-directory-index-acceptance-archive-gate.md`
- 正式索引文件：`docs/zdoc-system-autonomy-index.md`
- 当前工作区状态：起步检查时 `git status --short` 无输出，工作区 clean。

## 020A 节点定位

- 本节点为“正式索引文件后续维护规则冻结门控”。
- 本节点只做 `docs/zdoc-system-autonomy-index.md` 后续维护规则冻结。
- 本节点不得修改正式索引文件 `docs/zdoc-system-autonomy-index.md`。
- 本节点不是功能实现节点。
- 本节点不修改任何代码、配置、测试、prompt、runtime、endpoint、localhost、Ollama、模型推理、真实 KG、真实项目资料、secrets、output、job、export 或 log。
- 本节点不重命名、移动、删除或改写任何既有文档。
- 本节点不进入 `SYSTEM-AUTONOMY-020B` 或任何后续节点。
- 本节点不进入 `LOCAL-LAUNCHER-026`。

## 019A 至 019B 闭环承接

- `SYSTEM-AUTONOMY-019A` 已新增正式索引文件 `docs/zdoc-system-autonomy-index.md`。
- `SYSTEM-AUTONOMY-019B` 已完成正式索引文件验收与归档。
- `SYSTEM-AUTONOMY-020A` 仅固化后续维护规则，不修改索引文件。
- 后续如需维护索引文件，必须另设专项节点。
- 维护索引文件时，专项节点必须明确允许修改 `docs/zdoc-system-autonomy-index.md`。
- 未经专项节点授权，任何普通节点完成后均不得自动追加、修订或重排正式索引文件。

## 正式索引文件维护触发条件

以下条件只表示“可以考虑生成索引维护专项节点”，不表示当前节点允许修改索引：

- 新增 `SYSTEM-AUTONOMY` 节点后需要补充索引。
- 新增 tag 后需要登记索引。
- 新增治理文档后需要登记产物文件。
- 新增独立专线规则后需要登记禁止跳转关系。
- 发现索引遗漏但历史节点真实存在。
- 总控明确生成索引维护专项节点。
- 维护前需要把新增节点对应的 commit、tag、产物文件和后续约束作用写入索引。
- 不得因普通节点完成而自动修改索引；普通节点只能在回报中建议是否需要另设索引维护专项节点。

## 正式索引文件维护禁止规则

- 禁止自动修改索引文件。
- 禁止在非索引维护节点中修改索引文件。
- 禁止改写历史节点事实。
- 禁止删除历史节点记录。
- 禁止修改历史 commit hash。
- 禁止修改历史 tag。
- 禁止把未完成节点写入已完成索引。
- 禁止引用未确认文件内容。
- 禁止触碰代码、runtime、prompt、真实数据、output、log。
- 禁止进入青天评标仓库。
- 禁止自动进入 `LOCAL-LAUNCHER-026`。
- 禁止通过索引维护节点授予功能实现、runtime、endpoint、localhost、Ollama 或模型推理权限。
- 禁止将候选节点、推荐节点或未授权节点写成已完成事实。

## 索引维护专项节点规则

如后续允许修改 `docs/zdoc-system-autonomy-index.md`，专项节点必须至少写明：

| 必填项 | 要求 |
| --- | --- |
| 节点名称 | 必须明确为索引维护专项节点或等价的索引更新门控节点。 |
| 起始 HEAD | 必须写明开始前预期 HEAD，并在起步检查中验证。 |
| 起始 tag | 必须写明开始前预期 tag，并在起步检查中验证。 |
| 是否需要新开 Codex 对话框 | 必须明确是否沿用当前仓库对话框；跨仓库任务必须新开对应仓库对话框。 |
| 目标仓库 | 必须明确为 `/Users/youfeini/Desktop/文档生成系统`，除非总控另设其他仓库节点。 |
| 是否启用目标模式 | 必须明确启用或不启用；连续门控默认启用目标模式。 |
| 允许修改文件清单 | 必须列出 `docs/zdoc-system-autonomy-index.md`，并说明是否还有其他授权文件。 |
| 是否仅允许修改索引文件 | 必须明确是或否；默认仅允许修改正式索引文件。 |
| 禁止修改的历史节点文档清单 | 必须列出不得修改的历史节点文档，至少覆盖 015A 至当时最新已归档节点。 |
| 禁止进入的受保护区域 | 必须列出 runtime、endpoint、localhost、Ollama、模型推理、prompt、真实 KG、真实项目资料、secrets、output、job、export、log、青天评标仓库和 `LOCAL-LAUNCHER-026`。 |
| 质量检查命令 | 必须仅使用总控授权的静态 diff 与 git 状态检查，除非另有明确授权。 |
| commit message | 必须由专项节点明确给出。 |
| tag | 必须由专项节点明确给出。 |
| 完成回报格式 | 必须列出是否仅修改授权文件、commit、tag、push、远端指向、diff 和 status 收口状态。 |
| 完成后必须停止 | 必须明确不得自动进入下一节点或专线任务。 |

## 索引维护内容字段规则

后续更新索引时，新增记录至少应包含：

| 字段 | 记录要求 |
| --- | --- |
| 节点编号 | 记录新增或维护对象的 `SYSTEM-AUTONOMY` 节点编号。 |
| 节点名称 | 记录节点完整名称，不重写节点原文标题。 |
| 节点类型 | 记录授权门控、方案门控、执行门控、验收归档门控、维护门控等类型。 |
| 产物文件 | 记录该节点实际新增或维护的授权产物文件。 |
| commit hash | 记录节点完成提交，不得伪造或改写历史 commit。 |
| tag | 记录节点完成 tag，不得移动、删除或重指历史 tag。 |
| 完成状态 | 只将已完成且已提交/tag 的节点写为已完成。 |
| 是否文档节点 | 基于节点授权和实际 diff 记录。 |
| 是否功能实现节点 | 基于节点授权和实际 diff 记录，不得推断未确认内容。 |
| 是否修改代码 | 基于提交文件清单和节点验收记录。 |
| 是否触碰受保护区域 | 基于节点验收和实际操作记录记录。 |
| 后续约束作用 | 摘要该节点对后续工作的边界约束，不替代节点原文。 |
| 下一节点建议或衔接节点 | 记录节点给出的历史建议或实际衔接关系，不自动进入下一节点。 |

## 索引维护验收规则

后续任何索引维护专项节点，至少必须满足以下验收规则：

- 工作区 clean 起步。
- 分支必须为 `main`。
- HEAD 必须与起始 HEAD 一致。
- 仅允许修改指定索引文件。
- 不得修改历史节点文档。
- 不得新增非授权文件。
- 不得触碰代码与受保护区域。
- `git diff --check` 通过。
- `git diff --cached --check` 通过。
- commit hash 已回报。
- tag 已创建。
- `origin/main` 指向完成 HEAD。
- 远端 tag 指向完成 HEAD。
- 完成后工作区 clean。
- 完成后暂存区 clean。
- 完成后不得自动进入下一节点、`LOCAL-LAUNCHER-026` 或任何功能实现任务。

## 下一阶段治理入口候选

以下仅列候选，不在本节点执行：

- `SYSTEM-AUTONOMY-020B`：索引维护规则验收归档节点。
- `SYSTEM-AUTONOMY-021A`：下一阶段治理入口候选节点。
- `LOCAL-LAUNCHER-026`：独立专线，当前禁止自动进入。

## 推荐下一节点

从总控角度，推荐下一节点为 `SYSTEM-AUTONOMY-020B`。

推荐理由：020A 冻结索引维护规则后，应先完成维护规则验收归档，再决定是否进入下一阶段治理入口。

`SYSTEM-AUTONOMY-020B` 仍必须保持文档类、低风险、单文件，不得修改正式索引文件，不得修改历史节点文档，不得进入代码实现、runtime、endpoint、localhost、Ollama、模型推理、prompt、真实 KG、真实项目资料、secrets、output、job、export、log、青天评标仓库或 `LOCAL-LAUNCHER-026`。

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
- 不得进入 `SYSTEM-AUTONOMY-020B` 或任何后续节点。
- 不得进入青天评标仓库。
- 不得进入 runtime / endpoint / localhost / Ollama / 模型推理。
- 不得进入 prompt / 真实 KG / 真实项目资料 / secrets。
- 不得进入 output / job / export / log。
- 不得修改正式索引文件 `docs/zdoc-system-autonomy-index.md`。
- 不得实际重命名、移动、删除或改写任何既有文档。

## 最终收口说明

- `SYSTEM-AUTONOMY-020A` 完成后，`SYSTEM-AUTONOMY` 正式索引文件后续维护规则已冻结。
- `SYSTEM-AUTONOMY-020A` 仅新增本维护规则冻结文档，不改变任何既有文件。
- `SYSTEM-AUTONOMY-020A` 完成后不得自动进入 `SYSTEM-AUTONOMY-020B` 或 `LOCAL-LAUNCHER-026`。

## 本节点验收标准

- 仅新增本文档 1 个授权文件。
- 不修改正式索引文件 `docs/zdoc-system-autonomy-index.md`。
- 不修改 015A 至 019B 既有节点文档。
- 不实际重命名、移动、删除或改写任何既有文档。
- 不新增除本文档以外的任何文件。
- 不修改任何代码文件、配置文件、测试文件或 prompt 文件。
- 不运行测试、编译、服务、浏览器、localhost、runtime、endpoint、Ollama 或模型推理。
- 不触碰 prompt、真实 KG、真实项目资料、secrets、output、job、export、log。
- 不进入或修改青天评标仓库。
- 不进入 `LOCAL-LAUNCHER-026`。
- 不进入 `SYSTEM-AUTONOMY-020B` 或任何后续节点。
- `git diff --check` 通过。
- `git diff --cached --check` 通过。
- 提交并创建 tag：`v0.1.697-system-autonomy-020a-index-maintenance-rules-freeze-gate`。
