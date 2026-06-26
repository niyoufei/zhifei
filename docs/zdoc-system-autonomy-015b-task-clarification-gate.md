# SYSTEM-AUTONOMY-015B-TASK-CLARIFICATION-GATE

## 当前基线确认

- 目标仓库路径：`/Users/youfeini/Desktop/文档生成系统`
- 当前分支：`main`
- 起始 HEAD：`ba22cbfcc25a9081b7c00251494922dbe30ccce1`
- 起始 tag：`v0.1.682-system-autonomy-015-scope-authorization-gate`
- 上一节点：`SYSTEM-AUTONOMY-015A-SCOPE-AUTHORIZATION-DOCUMENT-GATE`
- 上一节点产物文件：`docs/zdoc-system-autonomy-015-scope-and-authorization-gate.md`

## 015B 节点定位

本节点是 `SYSTEM-AUTONOMY-015B` 的任务明确化门控节点，只用于确认后续任务边界、执行对象、禁止项和进入条件。

本节点不是功能实现节点，不启动任何实现动作，不进入 `SYSTEM-AUTONOMY-015C`，也不进入 `LOCAL-LAUNCHER-026`。

## 允许范围

- 仅允许新增本文档：`docs/zdoc-system-autonomy-015b-task-clarification-gate.md`。
- 仅允许围绕 `SYSTEM-AUTONOMY` 后续任务边界进行文字化明确。
- 仅允许记录后续节点进入条件、禁止边界和执行偏差防控规则。

## 禁止范围

- 禁止修改任何代码文件。
- 禁止修改配置文件、测试文件或 prompt 文件。
- 禁止启动服务。
- 禁止运行 pytest、py_compile、浏览器、localhost、runtime、endpoint、Ollama、模型推理。
- 禁止接触真实 KG、真实项目资料、prompt、secrets、output、job、export、log。
- 禁止进入或修改青天评标仓库：`/Users/youfeini/Desktop/ZhiFei_BizSystem`。
- 禁止进入 `LOCAL-LAUNCHER-026` 或任何 launcher 实现。

## 后续节点进入条件

- `SYSTEM-AUTONOMY-015C` 必须等待用户再次明确授权后才能进入。
- `LOCAL-LAUNCHER-026` 必须另行建立专线授权节点后才能进入。
- 未获得用户明确授权前，不得自动进入下一节点。
- 后续节点必须重新声明目标、允许文件、禁止范围、验证命令和停止条件。

## 执行偏差防控

- 吸收 `SYSTEM-AUTONOMY-015A` 中首次读取附件时 cwd 位于 `/Users/youfeini/Desktop/ZhiFei_BizSystem` 的偏差教训。
- 固化规则：任何节点开始前，必须先执行 `pwd` 并确认当前仓库根路径为 `/Users/youfeini/Desktop/文档生成系统`。
- 若 `pwd` 不在目标仓库，必须先切换到目标仓库，并重新回报 `pwd`、`git status --short`、`git rev-parse HEAD`、`git branch --show-current`。
- 禁止在非目标仓库 cwd 下读取附件、执行检查、写入文件或进行 git 操作。

## 本节点验收标准

- 仅新增本文档 1 个授权文件。
- 不修改任何代码文件、配置文件、测试文件或 prompt 文件。
- 不触碰 runtime / endpoint / localhost / Ollama / 模型推理。
- 不触碰真实 KG、真实项目资料、secrets、output、job、export、log。
- 不进入或修改青天评标仓库。
- `git diff --check` 通过。
- `git diff --cached --check` 通过。
- 提交并创建 tag：`v0.1.683-system-autonomy-015b-task-clarification-gate`。
