# SYSTEM-AUTONOMY-006 Controlled Code Implementation No Runtime Gate

## 1. 节点定位

`SYSTEM-AUTONOMY-006-CONTROLLED-CODE-IMPLEMENTATION-NO-RUNTIME-GATE` 是 ZDoc / 本地 AI 应用 / 系统自治建设路线的受控代码实现节点。

本节点不是 runtime ready、不是 endpoint ready、不是 dry-run ready、不是 trial ready、不是正式使用 ready。本节点只新增纯 Python 静态治理守卫、对应测试源码和本记录文档。

## 2. 当前状态机定位

当前状态机定位为 `S6_CODE_CHANGE_IMPLEMENTATION_NO_RUNTIME`。

本节点不得进入 `S7_STATIC_VALIDATION_ONLY`、`S8_RUNTIME_PREFLIGHT_AUTHORIZATION_REQUIRED` 或任何 runtime / endpoint / dry-run / trial / production 状态。

## 3. 实际新增 / 修改文件清单

实际新增文件：

1. `backend/zhifei_autoplan/system_autonomy_permissions.py`
2. `backend/zhifei_autoplan/system_autonomy_state_machine.py`
3. `backend/zhifei_autoplan/system_autonomy_evidence.py`
4. `backend/zhifei_autoplan/system_autonomy_static_guard.py`
5. `backend/tests/test_system_autonomy_permissions.py`
6. `backend/tests/test_system_autonomy_state_machine.py`
7. `backend/tests/test_system_autonomy_evidence.py`
8. `backend/tests/test_system_autonomy_static_guard.py`
9. `docs/zdoc-system-autonomy-controlled-code-implementation-no-runtime-gate-system-autonomy-006.md`

实际修改文件：无既有文件修改；仅新增白名单文件。

## 4. 新增代码文件职责

1. `system_autonomy_permissions.py`：定义权限维度、审批等级、治理模式、默认禁止项和纯函数权限校核。
2. `system_autonomy_state_machine.py`：定义 S0-S15/SX 状态枚举、S6 允许/禁止动作、转换规则和纯函数状态校核。
3. `system_autonomy_evidence.py`：定义 Gate 回报字段模板、禁止项确认字段和证据完整性校核。
4. `system_autonomy_static_guard.py`：基于传入路径字符串、命令字符串和变更文件列表做静态风险判定。

## 5. 测试源码覆盖意图

1. `test_system_autonomy_permissions.py`：覆盖默认禁止 runtime、endpoint、Ollama、模型推理、prompt，及证据缺失阻断。
2. `test_system_autonomy_state_machine.py`：覆盖禁止跨越到 007/后续 runtime 状态、S6 禁止动作和阻断状态。
3. `test_system_autonomy_evidence.py`：覆盖证据链字段缺失阻断和禁止项确认触发阻断。
4. `test_system_autonomy_static_guard.py`：覆盖真实 KG / 项目资料、secrets、output/job/export/log、runtime 脚本、Web UI、endpoint、Ollama、模型/prompt 命令风险和 006 白名单变更文件。

测试源码仅写入，未运行 pytest / unittest / test suite。

## 6. 白名单范围确认

本节点仅新增第 3 节列出的 9 个文件。未新增、修改、删除、移动、重命名任何非白名单文件。

## 7. 禁止修改范围确认

未修改 `local-launcher-v1` 静态 UI 文件、runtime 脚本、Web UI 启动脚本、FastAPI router、endpoint 文件、API 入口文件、模型接入文件、KG 接入文件、output guard 真实运行链路文件、production 配置、`.env` / secrets / credentials、真实 KG、真实项目资料、output / job / export / log 正文。

## 8. 禁止 runtime 执行确认

本节点未启动、停止或重启服务；未执行 Web UI 启动脚本；未打开、预览或运行 HTML 页面；未访问 endpoint；未执行 curl / HTTP request / localhost / 端口探测；未读取、清理、删除 `.runtime/docgen/` PID 文件。

## 9. 禁止 endpoint / Ollama / 模型 / prompt / KG / 真实资料确认

本节点未运行 Ollama 或任何模型命令，未进行模型推理，未向本地模型、远程模型或系统应用输入 prompt，未读取真实 KG / 真实项目资料 / 招标文件 / 图纸 / 清单 / 项目样本。

## 10. 静态实现策略

新增模块只使用 `dataclasses`、`enum`、`typing`、`pathlib.PurePosixPath` 和 `shlex`。所有函数仅处理显式传入的数据结构、路径字符串、命令字符串和文件列表，不读取文件系统正文，不读取环境变量，不访问网络，不执行 subprocess，不启动服务，不注册 endpoint，不调用模型，不接入 KG。

## 11. 未运行测试说明

按本节点附件约束，未运行 pytest、unittest 或任何 test suite。测试源码仅作为后续 Gate 可审核的静态源码落盘。

## 12. `py_compile` 校验证据

已执行：

`python3 -B -m py_compile backend/zhifei_autoplan/system_autonomy_permissions.py backend/zhifei_autoplan/system_autonomy_state_machine.py backend/zhifei_autoplan/system_autonomy_evidence.py backend/zhifei_autoplan/system_autonomy_static_guard.py backend/tests/test_system_autonomy_permissions.py backend/tests/test_system_autonomy_state_machine.py backend/tests/test_system_autonomy_evidence.py backend/tests/test_system_autonomy_static_guard.py`

结果：退出码 0，无报错输出。

## 13. git diff 校验证据

已执行：

`git diff --check -- backend/zhifei_autoplan/system_autonomy_permissions.py backend/zhifei_autoplan/system_autonomy_state_machine.py backend/zhifei_autoplan/system_autonomy_evidence.py backend/zhifei_autoplan/system_autonomy_static_guard.py backend/tests/test_system_autonomy_permissions.py backend/tests/test_system_autonomy_state_machine.py backend/tests/test_system_autonomy_evidence.py backend/tests/test_system_autonomy_static_guard.py docs/zdoc-system-autonomy-controlled-code-implementation-no-runtime-gate-system-autonomy-006.md`

结果：退出码 0，无报错输出。

已执行：

`git diff --cached --check`

结果：退出码 0，无报错输出。

已执行：

`git diff --cached --name-status`

结果：

```text
A	backend/tests/test_system_autonomy_evidence.py
A	backend/tests/test_system_autonomy_permissions.py
A	backend/tests/test_system_autonomy_state_machine.py
A	backend/tests/test_system_autonomy_static_guard.py
A	backend/zhifei_autoplan/system_autonomy_evidence.py
A	backend/zhifei_autoplan/system_autonomy_permissions.py
A	backend/zhifei_autoplan/system_autonomy_state_machine.py
A	backend/zhifei_autoplan/system_autonomy_static_guard.py
A	docs/zdoc-system-autonomy-controlled-code-implementation-no-runtime-gate-system-autonomy-006.md
```

## 14. 风险清单

1. 当前模块尚未接入任何 runtime，因此只能提供静态治理能力，不能代表运行链路已受保护。
2. 测试源码未运行，功能正确性仅由语法检查和静态 diff 检查支撑。
3. 路径和命令风险判定为保守字符串规则，后续如需更强覆盖，应在独立 Gate 中扩展。

## 15. 回滚策略

如本节点需回滚，建议在后续授权下 revert 本节点提交；不得擅自执行 destructive git 操作、删除用户文件、reset、checkout 或清理运行产物。

## 16. 后续 Gate 建议

后续 Gate 原则上建议为 `SYSTEM-AUTONOMY-007-STATIC-VALIDATION-ONLY-GATE`。

明确限制：

1. 本节点不得进入 007。
2. 007 是否允许运行测试须由 ChatGPT 总控师审核后决定。
3. 007 默认仍禁止 runtime。
4. 007 默认禁止 endpoint。
5. 007 默认禁止 Ollama。
6. 007 默认禁止模型推理。
7. 007 默认禁止 prompt。
8. 007 默认禁止真实 KG / 真实项目资料。
9. 007 必须由 ChatGPT 总控师明确授权后才可执行。
