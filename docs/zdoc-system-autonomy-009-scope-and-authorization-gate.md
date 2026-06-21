# SYSTEM-AUTONOMY-009 Scope And Authorization Gate

## 1. Node

Node:

`SYSTEM-AUTONOMY-009-SCOPE-AND-AUTHORIZATION-GATE`

性质：

1. docs-only
2. code-read-only allowed
3. no code modification
4. no test modification
5. no runtime
6. no endpoint
7. no Ollama
8. no model inference
9. no prompt input
10. no real KG / real project data read
11. no secrets / output / job / export / log body reading
12. stopped before `SYSTEM-AUTONOMY-009-IMPLEMENTATION`
13. stopped before `LOCAL-LAUNCHER-026`

## 2. Start Baseline

开始前 HEAD：

`eb1403ca3e2d00ea7b89f48fbd7526cb46da7c89`

开始前 exact tag：

`v0.1.661-system-autonomy-008-revalidation-gate`

当前分支：

`main`

开始前 `git status --short`：

无输出，工作区 clean。

## 3. Read-Only Checks Performed

已执行只读状态核查：

1. `git status --short`
2. `git rev-parse HEAD`
3. `git describe --tags --exact-match HEAD`
4. `git rev-parse --abbrev-ref HEAD`

已只读查看 008 收口 docs：

1. `docs/zdoc-system-autonomy-008-revalidation-1-static-validation-only-gate.md`
2. `docs/zdoc-system-autonomy-008-implementation-static-guard-scope-correction-no-runtime.md`
3. `docs/zdoc-system-autonomy-008-scope-and-authorization-gate.md`

已只读查看必要 system autonomy 代码边界文件：

1. `backend/zhifei_autoplan/system_autonomy_static_guard.py`

未读取 runtime、endpoint、Ollama、模型接入、真实 KG、真实项目资料、secrets、output、job、export 或 log 正文。

## 4. SYSTEM-AUTONOMY-008 Closure Status

008 链路已完成收口。

确认事实：

1. 008 implementation 已完成。
2. 008 revalidation 已通过。
3. 当前基线为 `v0.1.661-system-autonomy-008-revalidation-gate`。
4. 008 implementation 的实际授权修改范围为：
   - `backend/zhifei_autoplan/system_autonomy_static_guard.py`
   - `backend/tests/test_system_autonomy_static_guard.py`
   - `docs/zdoc-system-autonomy-008-implementation-static-guard-scope-correction-no-runtime.md`
5. 008 revalidation 记录的最小验证已通过，并在 revalidation 节点停止于 `SYSTEM-AUTONOMY-009` 之前。

## 5. SYSTEM-AUTONOMY-009 Suggested Positioning

建议将 `SYSTEM-AUTONOMY-009` 定位为：

`controlled static-guard scope advancement / authorization-only implementation gate`

建议目标仅限于在后续明确授权后，继续围绕 system autonomy 静态守卫做最小范围推进：将 008 阶段收口后的静态授权范围、阻断原因命名和对应最小测试推进到 009 阶段。

009 不应被定义为 runtime ready、endpoint ready、dry-run ready、trial ready、KG ready、real-project ready、prompt ready 或 production ready。

009 scope gate 本身仅形成下一节点授权请求，不直接实施。

## 6. Suggested Allowed Files For 009 Implementation Node

若后续由 ChatGPT 总控明确授权进入 `SYSTEM-AUTONOMY-009-IMPLEMENTATION`，建议允许修改范围限于：

1. `backend/zhifei_autoplan/system_autonomy_static_guard.py`
2. `backend/tests/test_system_autonomy_static_guard.py`
3. `docs/zdoc-system-autonomy-009-implementation-static-guard-scope-correction-no-runtime.md`

建议仅允许：

1. 将 `AUTHORIZED_CHANGED_FILES` 从 008 阶段实现记录推进到 009 阶段实现记录。
2. 将 changed-file 越界阻断原因从 008 阶段命名推进到 009 阶段命名。
3. 补充或更新与 009 静态守卫授权范围直接对应的最小测试。
4. 新增 1 个 docs-only 009 implementation 记录文件。

不得在实现节点中扩大为 runtime、endpoint、Ollama、模型推理、prompt、真实 KG、真实项目资料或生成结果链路验证。

## 7. Suggested Prohibited Files For 009 Implementation Node

若后续进入实现节点，建议继续禁止触碰：

1. runtime 启动脚本：`scripts/run_web_ui.sh`、`scripts/start_web_ui_background.sh`、`scripts/stop_web_ui_background.sh`、`scripts/web_ui_watchdog.sh`
2. Web UI / launcher：`local-launcher-v1/`、`frontend_web/`、`frontend/`
3. endpoint / API：`backend/app/routers/`、`backend/app/main.py`、`api/server.py`
4. 模型接入：`providers/`、`llm_client.py`、`ollama_preview.py`
5. KG 接入或真实 KG 路径：`kg/`、`kg_packs/`、`backend/kg_packs/`、`backend/data/kg/`
6. 真实项目资料路径：`backend/data/uploads/`、`backend/data/extracts/`、`data/uploads/`、`data/extracts/`
7. secrets / credentials：`.env*`、`secrets/`、`tokens/`、`credentials/`
8. output / job / export / log：`output/`、`outputs/`、`job/`、`jobs/`、`export/`、`exports/`、`log/`、`logs/`、`.runtime/docgen/`
9. 配置文件、脚本、非授权测试、非授权 docs、生成结果、导出物和日志正文。

## 8. 009 Risk Boundaries

runtime 风险：

后续实现不得启动服务、后台进程、watchdog、Web UI 或任何 runtime 链路；不得修改 runtime 启动脚本或部署启动配置。

endpoint 风险：

后续实现不得注册、修改、访问或探测 endpoint；不得执行 curl、HTTP request、localhost 或端口探测。

Ollama / 模型推理风险：

后续实现不得运行 Ollama，不得调用模型命令，不得新增或修改模型 provider 接入，不得进行任何模型推理。

prompt 输入风险：

后续实现不得输入 prompt，不得构造真实 prompt，不得使用真实业务文本触发模型链路。

真实 KG / 项目资料读取风险：

后续实现不得读取真实 KG、真实项目资料、招标文件、图纸、清单、项目样本或业务数据正文。

secrets / output / job / export / log 正文读取风险：

后续实现不得读取 secrets、tokens、credentials、env 敏感信息正文、output、job、export、生成结果或 log 正文。

## 9. Suggested Validation For 009 Implementation Node

若后续明确授权进入实现节点，建议验证方式限于静态和最小测试：

1. `python3 -B -m py_compile backend/zhifei_autoplan/system_autonomy_static_guard.py`
2. `python3 -m pytest -q backend/tests/test_system_autonomy_static_guard.py`
3. `git diff --check`

不得将上述验证扩展为 runtime、endpoint、Ollama、模型推理、prompt 输入、真实 KG、真实项目资料或日志正文读取。

## 10. Recommendation

是否建议进入 009 实现节点：

是。建议进入 `SYSTEM-AUTONOMY-009-IMPLEMENTATION`，但必须由 ChatGPT 总控明确授权后才可执行。

本节点不得直接实施。

## 11. Next Node Authorization Request

建议下一节点为：

`SYSTEM-AUTONOMY-009-IMPLEMENTATION-STATIC-GUARD-SCOPE-CORRECTION-NO-RUNTIME`

建议下一节点性质：

1. minimal code fix
2. static validation only
3. docs record
4. no runtime
5. no endpoint
6. no Ollama
7. no model inference
8. no prompt input
9. no real KG / real project data read
10. no secrets / output / job / export / log body read

建议下一节点授权修改范围仅限：

1. `backend/zhifei_autoplan/system_autonomy_static_guard.py`
2. `backend/tests/test_system_autonomy_static_guard.py`
3. `docs/zdoc-system-autonomy-009-implementation-static-guard-scope-correction-no-runtime.md`

必须禁止下一节点直接进入 `LOCAL-LAUNCHER-026` 或任何后续节点。

## 12. Prohibited Scope Confirmation

本节点未新增、修改或删除任何代码文件。

本节点未修改任何测试文件。

本节点未修改配置、脚本、runtime、Web UI、endpoint、API、模型接入或 KG 接入文件。

本节点未启动 runtime。

本节点未启动 Web UI。

本节点未访问 endpoint。

本节点未执行 curl / HTTP request / localhost / 端口探测。

本节点未运行 Ollama。

本节点未运行任何模型命令。

本节点未进行模型推理。

本节点未输入 prompt。

本节点未读取真实 KG。

本节点未读取真实项目资料。

本节点未读取 secrets / tokens / credentials / env 敏感信息正文。

本节点未读取 output / job / export / log 正文。

本节点未进入 `SYSTEM-AUTONOMY-009-IMPLEMENTATION`。

本节点未进入 `LOCAL-LAUNCHER-026`。

本节点未自行进入任何后续节点。

## 13. Conclusion

`SYSTEM-AUTONOMY-009 SCOPE AUTHORIZATION PREPARED / DOCS ONLY / NO CODE MODIFIED / NO RUNTIME / NO ENDPOINT / NO OLLAMA / NO MODEL INFERENCE / NO REAL DATA / STOPPED BEFORE IMPLEMENTATION`
