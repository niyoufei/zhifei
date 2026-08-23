# SYSTEM-AUTONOMY-007 Static Validation Only Gate

## 1. 节点定位

本文件记录 `SYSTEM-AUTONOMY-007-STATIC-VALIDATION-ONLY-GATE` 的静态验证结果。

本节点为 `static validation only + docs record`，仅对 `SYSTEM-AUTONOMY-006` 新增系统自治治理守卫代码执行受限静态验证，并记录验证结果。

本节点不修改代码、脚本、配置、测试、静态 UI、数据文件；不启动 runtime；不启动服务；不启动 Web UI；不访问 endpoint；不运行 Ollama；不执行模型命令；不进行模型推理；不输入 prompt；不读取真实 KG、真实项目资料、招标文件、图纸、清单、项目样本；不读取 secrets、tokens、credentials、output、job、export、生成结果或日志正文。

## 2. 当前状态机定位

`S7_STATIC_VALIDATION_ONLY`

## 3. 006 完成态 HEAD / tag

006 完成态 HEAD：

`825e00a2c34c9bafb8af3c5e44e0754465b7b021`

006 完成态 tag：

`v0.1.655-system-autonomy-controlled-code-implementation-no-runtime-gate`

006 补审结论：

`SYSTEM-AUTONOMY-006 COMPLETED / RECOVERY AUDIT PASSED / CONTROLLED CODE IMPLEMENTATION NO RUNTIME / WHITELIST ONLY / STATIC PY_COMPILE PASSED / NO RUNTIME EXECUTION / STOPPED`

## 4. 本节点开始前 HEAD / tag

开始前 HEAD：

`825e00a2c34c9bafb8af3c5e44e0754465b7b021`

开始前 tag：

`v0.1.655-system-autonomy-controlled-code-implementation-no-runtime-gate`

开始前 `git status --short`：

无输出，工作区 clean。

开始前 `git diff --check HEAD`：

无输出，未发现 whitespace error。

## 5. 本节点实际读取文件

实际读取：

1. `/Users/youfeini/.codex/attachments/1b67ba10-5ba3-4e56-9798-a11e9c360d26/pasted-text.txt`
2. `backend/zhifei_autoplan/system_autonomy_permissions.py`
3. `backend/zhifei_autoplan/system_autonomy_state_machine.py`
4. `backend/zhifei_autoplan/system_autonomy_evidence.py`
5. `backend/zhifei_autoplan/system_autonomy_static_guard.py`
6. `backend/tests/test_system_autonomy_permissions.py`
7. `backend/tests/test_system_autonomy_state_machine.py`
8. `backend/tests/test_system_autonomy_evidence.py`
9. `backend/tests/test_system_autonomy_static_guard.py`
10. `docs/zdoc-system-autonomy-controlled-code-implementation-no-runtime-gate-system-autonomy-006.md`

未读取 001-005 docs 文件；本节点实际验证未需要继续读取 001-005 docs 文件。

## 6. 本节点实际执行命令

实际执行：

1. `git status --short`
2. `git rev-parse HEAD`
3. `git tag --points-at HEAD`
4. `git diff --check HEAD`
5. `python3 -B -m py_compile backend/zhifei_autoplan/system_autonomy_permissions.py backend/zhifei_autoplan/system_autonomy_state_machine.py backend/zhifei_autoplan/system_autonomy_evidence.py backend/zhifei_autoplan/system_autonomy_static_guard.py`
6. `python3 -m pytest -q backend/tests/test_system_autonomy_permissions.py backend/tests/test_system_autonomy_state_machine.py backend/tests/test_system_autonomy_evidence.py backend/tests/test_system_autonomy_static_guard.py`
7. `rg -n "curl|localhost|ollama|subprocess|requests|FastAPI|APIRouter|open\\(|\\.env|secrets|output|export|job|prompt" backend/zhifei_autoplan/system_autonomy_permissions.py backend/zhifei_autoplan/system_autonomy_state_machine.py backend/zhifei_autoplan/system_autonomy_evidence.py backend/zhifei_autoplan/system_autonomy_static_guard.py backend/tests/test_system_autonomy_permissions.py backend/tests/test_system_autonomy_state_machine.py backend/tests/test_system_autonomy_evidence.py backend/tests/test_system_autonomy_static_guard.py docs/zdoc-system-autonomy-controlled-code-implementation-no-runtime-gate-system-autonomy-006.md`

未执行 runtime、服务启动、Web UI 启动、curl、HTTP request、localhost / 端口探测、Ollama、模型命令、模型推理、prompt 输入、generation、export 或 write-back 命令。

## 7. py_compile 结果

命令：

`python3 -B -m py_compile backend/zhifei_autoplan/system_autonomy_permissions.py backend/zhifei_autoplan/system_autonomy_state_machine.py backend/zhifei_autoplan/system_autonomy_evidence.py backend/zhifei_autoplan/system_autonomy_static_guard.py`

结果：

通过。命令退出码为 `0`，无输出。

## 8. 定向 pytest 结果

命令：

`python3 -m pytest -q backend/tests/test_system_autonomy_permissions.py backend/tests/test_system_autonomy_state_machine.py backend/tests/test_system_autonomy_evidence.py backend/tests/test_system_autonomy_static_guard.py`

结果：

失败。命令退出码为 `1`。

统计：

`1 failed, 13 passed in 0.06s`

失败用例：

`backend/tests/test_system_autonomy_static_guard.py::test_path_guard_blocks_real_kg_project_data_secrets_and_outputs`

失败断言：

`assert result.allowed is False`

实际结果：

`StaticGuardResult(allowed=True, risk_categories=(), blocked_items=(), blocked_reasons=()).allowed`

阻断含义：

静态守卫路径风险测试期望阻断真实 KG、真实项目资料、secrets、output/job/export/log 相关路径，但实际返回 `allowed=True`。因此，本节点不能确认 006 新增静态守卫路径风险阻断逻辑通过验证。

## 9. 越界关键词检索结果

命令：

`rg -n "curl|localhost|ollama|subprocess|requests|FastAPI|APIRouter|open\\(|\\.env|secrets|output|export|job|prompt" backend/zhifei_autoplan/system_autonomy_permissions.py backend/zhifei_autoplan/system_autonomy_state_machine.py backend/zhifei_autoplan/system_autonomy_evidence.py backend/zhifei_autoplan/system_autonomy_static_guard.py backend/tests/test_system_autonomy_permissions.py backend/tests/test_system_autonomy_state_machine.py backend/tests/test_system_autonomy_evidence.py backend/tests/test_system_autonomy_static_guard.py docs/zdoc-system-autonomy-controlled-code-implementation-no-runtime-gate-system-autonomy-006.md`

结果：

发现关键词命中。命中主要分布在：

1. `backend/zhifei_autoplan/system_autonomy_static_guard.py` 的风险分类、路径关键词、命令关键词和阻断常量中；
2. `backend/zhifei_autoplan/system_autonomy_permissions.py`、`backend/zhifei_autoplan/system_autonomy_state_machine.py`、`backend/zhifei_autoplan/system_autonomy_evidence.py` 的枚举值或证据字段名中；
3. `backend/tests/test_system_autonomy_static_guard.py`、`backend/tests/test_system_autonomy_state_machine.py` 的静态测试样本和测试名称中；
4. `docs/zdoc-system-autonomy-controlled-code-implementation-no-runtime-gate-system-autonomy-006.md` 的 006 边界说明、负面确认和后续 Gate 建议中。

未在 006 新增代码文件中检索到 `requests`、`APIRouter` 或 `open(` 命中。

未在 006 新增代码文件中检索到 `subprocess` 命中；`subprocess` 命中仅出现在 006 docs 的负面说明中。

未在 006 新增代码文件中检索到 `FastAPI` 命中；`FastAPI` 命中仅出现在 006 docs 的负面说明中。

检索结果未显示 006 新增代码存在服务启动、HTTP 客户端调用、endpoint 注册、文件正文读取或 subprocess 执行关键词；但定向 pytest 已失败，静态守卫路径阻断逻辑未通过验证。

## 10. runtime 启动代码检查

基于本节点允许的关键词检索，未发现 006 新增代码文件中存在 runtime 启动代码关键词命中。

本节点未启动、停止或重启 runtime。

## 11. endpoint 访问代码检查

基于本节点允许的关键词检索，未发现 006 新增代码文件中存在 `requests`、`FastAPI`、`APIRouter`、`open(` 命中。

`curl`、`localhost` 相关命中出现在静态守卫命令关键词、测试样本或 006 docs 负面说明中，不代表本节点实际访问 endpoint。

本节点未执行 curl、HTTP request、localhost / 端口探测或 endpoint 访问。

## 12. Ollama / 模型命令代码检查

`ollama` 关键词命中出现在静态守卫风险分类、命令关键词、测试样本、枚举或 docs 说明中。

本节点未运行 Ollama，未执行任何模型命令。

## 13. 模型推理代码检查

`model` 相关命中未作为本节点关键词检索项单独检索；`prompt` 及 `ollama` 相关命中出现在枚举、证据字段、静态守卫常量、测试样本和 docs 说明中。

本节点未进行模型推理。

## 14. prompt 输入代码检查

`prompt` 关键词命中出现在枚举、证据字段、静态守卫命令关键词、测试样本和 docs 说明中。

本节点未向本地模型、远程模型或系统应用输入 prompt。

## 15. 真实 KG / 真实项目资料读取代码检查

本节点未读取真实 KG、真实项目资料、招标文件、图纸、清单或项目样本。

定向 pytest 已发现静态路径守卫阻断测试失败，因此不能确认 006 新增静态守卫路径风险阻断逻辑能正确阻断真实 KG / 真实项目资料相关路径。

## 16. secrets / output / job / export / log 正文读取代码检查

本节点未读取 secrets、tokens、credentials、环境变量敏感信息、output、job、export、生成结果或日志正文。

关键词命中显示 006 新增代码包含 `.env`、`secrets`、`output`、`job`、`export` 等风险分类或阻断关键词；但定向 pytest 已发现路径守卫阻断测试失败，因此不能确认该静态守卫路径阻断逻辑通过验证。

## 17. 是否修改代码

否。

## 18. 是否修改测试

否。

## 19. 是否启动服务

否。

## 20. 是否访问 endpoint

否。

## 21. 是否运行 Ollama

否。

## 22. 是否模型推理

否。

## 23. 是否输入 prompt

否。

## 24. 是否读取真实 KG / 真实项目资料

否。

## 25. 是否读取 secrets / output / job / export / log 正文

否。

## 26. 风险项

1. 定向 pytest 失败，失败用例为 `backend/tests/test_system_autonomy_static_guard.py::test_path_guard_blocks_real_kg_project_data_secrets_and_outputs`。
2. 静态路径守卫在测试场景中对真实 KG、真实项目资料、secrets、output/job/export/log 相关路径返回 `allowed=True`，与预期阻断行为不一致。
3. 因本节点禁止代码修复，本次未修改 006 新增代码或测试。

## 27. 阻断项

发现阻断项：

`backend/tests/test_system_autonomy_static_guard.py::test_path_guard_blocks_real_kg_project_data_secrets_and_outputs` 失败。

本节点结论为：

`STATIC VALIDATION FAILED / BLOCKED BY TARGETED PYTEST FAILURE / NO CODE MODIFIED / DOCS RECORD ONLY / STOPPED`

## 28. 回滚策略

本节点仅新增 docs 记录文件：

`docs/zdoc-system-autonomy-static-validation-only-gate-system-autonomy-007.md`

如需回滚本节点记录，可在后续明确授权后删除该 docs 文件或 revert 本节点提交。

如本节点 tag 已创建且需回滚，可在后续明确授权后删除 tag：

`v0.1.656-system-autonomy-static-validation-only-gate`

## 29. 后续 Gate 建议

原则上，后续 Gate 可规划为：

`SYSTEM-AUTONOMY-008-RUNTIME-PREFLIGHT-AUTHORIZATION-PREPARATION-GATE`

但必须明确：

1. 本节点不得进入 008；
2. 008 是否开启目标模式须由 ChatGPT 总控师审核后决定；
3. 008 是否允许读取 runtime 脚本须由 ChatGPT 总控师审核后决定；
4. 008 是否允许运行 runtime preflight 须由 ChatGPT 总控师审核后决定；
5. 008 默认禁止 endpoint；
6. 008 默认禁止 Ollama；
7. 008 默认禁止模型推理；
8. 008 默认禁止 prompt；
9. 008 默认禁止真实 KG / 真实项目资料；
10. 008 必须由 ChatGPT 总控师明确授权后才可执行。

由于本节点定向 pytest 失败，建议 ChatGPT 总控师先审核 `SYSTEM-AUTONOMY-007` 阻断项，再决定是否授权进入任何后续节点或回到代码修复节点。
