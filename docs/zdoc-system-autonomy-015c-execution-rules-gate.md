# SYSTEM-AUTONOMY-015C-EXECUTION-RULES-GATE

## 当前基线确认

- 仓库根路径：`/Users/youfeini/Desktop/文档生成系统`
- 当前分支：`main`
- 起始 HEAD：`626300ae67ee6bd938bd94537c05d1df6ae99a03`
- 起始 tag：`v0.1.683-system-autonomy-015b-task-clarification-gate`
- 上一节点名称：`SYSTEM-AUTONOMY-015B-TASK-CLARIFICATION-GATE`
- 上一节点产物文件：`docs/zdoc-system-autonomy-015b-task-clarification-gate.md`

## 015C 节点定位

- 本节点为 `SYSTEM-AUTONOMY-015C` 执行规则固化门控。
- 本节点不是功能实现节点。
- 本节点不进入 `SYSTEM-AUTONOMY-015D`，不进入 `LOCAL-LAUNCHER-026`。

## Codex 对话框连续性规则

- `SYSTEM-AUTONOMY` 连续门控节点原则上沿用同一 Codex 对话框。
- 禁止新建、派生、委派、并行启动其他 Codex 对话框。
- 只有另起专线任务时，才由总控明确标注是否新开 Codex 对话框。

## 目标模式规则

- 每次 Codex 指令上方必须明确：是否新开 Codex 对话框、是否启用“目标”模式。
- 连续门控节点默认启用“目标”模式。
- 目标模式下只执行当前节点，不得自动扩展到下一节点。

## 仓库边界规则

- 每个节点开始前必须先执行并回报 `pwd`。
- `pwd` 必须等于目标仓库根路径后，方可读取、检查、写入或 git 操作。
- 禁止在非目标仓库 cwd 下读取附件、执行命令或写入文件。
- 禁止进入或修改青天评标仓库：`/Users/youfeini/Desktop/ZhiFei_BizSystem`。

## 文件变更规则

- 每个节点必须明确允许新增或修改的文件清单。
- 未列入清单的文件一律不得 stage、提交、删除、移动或修改。
- 若出现非授权文件变化，必须立即停止并回报，不得自行修复。

## 禁止命令规则

- 禁止 fetch、pull、merge、rebase、reset、checkout、clean、stash。
- 禁止 pytest、py_compile、npm run、pnpm、yarn。
- 禁止启动服务、访问 localhost、调用 runtime、endpoint、Ollama、模型推理。
- 禁止接触 prompt、真实 KG、真实项目资料、secrets、output、job、export、log。

## 异常停止规则

- push rejected 立即停止。
- 远端不一致立即停止。
- 工作区出现非授权变化立即停止。
- 当前分支不是 `main` 立即停止。
- HEAD 不等于起始 HEAD 立即停止。
- cwd 不在目标仓库立即停止。
- 发现需要进入下一节点立即停止。

## 完成回报规则

- 必须回报开始前 HEAD、结束后 HEAD、commit hash、tag、远端 main 指向、远端 tag 指向。
- 必须回报 `git diff --name-only`、`git diff --cached --name-only`、`git status --short` 是否 clean。
- 必须回报是否仅变更授权文件。
- 必须回报是否未触碰禁止区域。
- 必须回报下一步建议，但不得自动执行下一步。

## 本节点验收标准

- 仅新增本文档 1 个授权文件。
- 不修改任何代码文件、配置文件、测试文件或 prompt 文件。
- 不运行测试、编译、服务、浏览器、localhost、runtime、endpoint、Ollama 或模型推理。
- 不触碰真实 KG、真实项目资料、secrets、output、job、export、log。
- 不进入青天评标仓库。
- 不进入 `LOCAL-LAUNCHER-026`。
- 不进入 `SYSTEM-AUTONOMY-015D` 或任何后续节点。
- `git diff --check` 通过。
- `git diff --cached --check` 通过。
- 提交并创建 tag：`v0.1.684-system-autonomy-015c-execution-rules-gate`。
