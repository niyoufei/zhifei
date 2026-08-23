# SYSTEM-AUTONOMY-007-FIX-1 Static Guard Path Blocklist Correction No Runtime Gate

## 1. 节点定位

本文件记录 `SYSTEM-AUTONOMY-007-FIX-1-STATIC-GUARD-PATH-BLOCKLIST-CORRECTION-NO-RUNTIME-GATE` 的修复与静态验证结果。

本节点为 `minimal code fix + static validation + docs record`，仅修复 `SYSTEM-AUTONOMY-007` 定向 pytest 暴露的 path guard 阻断规则问题。

本节点不是 runtime ready、不是 endpoint ready、不是 dry-run ready、不是 trial ready、不是正式使用 ready。

## 2. 目标模式

是否开启目标模式：否。

关闭理由：本节点是单点缺陷修复，目标明确，仅修复 007 定向 pytest 暴露的静态 path guard blocklist 问题，不需要目标模式；关闭目标模式可降低长上下文停滞风险。

## 3. 当前基线 HEAD / tag

开始前 HEAD：

`f9047796b3e0efff7bcaea83b1893f3bb4310849`

开始前 tag：

`v0.1.656-system-autonomy-static-validation-only-gate`

开始前分支：

`main`

开始前 `git status --short`：

无输出，工作区 clean。

## 4. 007 失败用例

失败用例：

`backend/tests/test_system_autonomy_static_guard.py::test_path_guard_blocks_real_kg_project_data_secrets_and_outputs`

007 记录中的失败统计：

`1 failed, 13 passed in 0.06s`

## 5. 失败原因定位

失败原因定位为静态 path guard 对部分禁止路径或风险路径的字符串识别不足：

1. `_normalize_path` 使用 `.lstrip("./")`，会把 `.env.local` 规范化为 `env.local`，导致 `.env` 风险标记丢失。
2. output / job / export / log 等目录如果作为目录本身出现，规范化后可能不带尾部 `/`，原有 `output/`、`job/`、`export/`、`logs/` 等标记覆盖不足。
3. KG / knowledge graph / real KG、真实项目资料、招标文件、图纸、清单、项目样本、secrets / tokens / credentials、`.runtime/docgen` 等静态 path 标记需要补齐。

以上定位仅基于传入路径字符串、测试样本和授权代码文件进行静态分析；未读取真实 KG、真实项目资料、output、job、export、log 或 secrets 正文。

## 6. 实际修改文件

实际修改文件：

1. `backend/zhifei_autoplan/system_autonomy_static_guard.py`

## 7. 实际新增文件

实际新增文件：

1. `docs/zdoc-system-autonomy-007-fix-1-static-guard-path-blocklist-correction-no-runtime.md`

## 8. 修复内容说明

本节点仅修改纯函数 / 静态字符串判定逻辑：

1. 修正 `_normalize_path`，只去除显式 `./` 前缀和绝对路径前导 `/`，保留 `.env.local` 等 dotfile 前缀。
2. 扩展 `FORBIDDEN_PATH_MARKERS`，补齐 KG / knowledge graph / real KG、真实项目资料、招标文件、图纸、清单、项目样本、secrets / tokens / credentials、output、job、export、log / logs、`.runtime/docgen` 等路径风险标记。
3. `analyze_path_string` 对规范化路径追加尾部斜杠形态进行静态匹配，使 `output`、`job`、`export`、`log` 等目录本身也能被同一 blocklist 命中。

未引入网络请求、subprocess、服务启动逻辑、FastAPI、APIRouter、endpoint、Ollama、模型推理、prompt 输入、文件正文读取、环境变量读取、写文件、命令执行或 import 时 I/O。

## 9. 白名单范围确认

本节点仅修改授权代码文件：

1. `backend/zhifei_autoplan/system_autonomy_static_guard.py`

本节点仅新增授权 docs 文件：

1. `docs/zdoc-system-autonomy-007-fix-1-static-guard-path-blocklist-correction-no-runtime.md`

未修改任何测试文件。

## 10. 禁止修改范围确认

未修改任何非授权代码、脚本、配置、测试、静态 UI 或数据文件。

未修改 runtime 脚本、Web UI、endpoint、Ollama / 模型接入、KG 接入、output guard 真实运行链路、production 配置、`.env`、secrets、credentials、真实 KG、真实项目资料、招标文件、图纸、清单、项目样本、output、job、export、生成结果或日志正文。

## 11. `py_compile` 结果

命令：

`python3 -B -m py_compile backend/zhifei_autoplan/system_autonomy_static_guard.py`

结果：

通过。命令退出码为 `0`，无输出。

## 12. 单失败用例 pytest 结果

命令：

`python3 -m pytest -q backend/tests/test_system_autonomy_static_guard.py::test_path_guard_blocks_real_kg_project_data_secrets_and_outputs`

结果：

通过。

统计：

`1 passed in 0.02s`

## 13. 4 个 006 测试文件定向 pytest 结果

命令：

`python3 -m pytest -q backend/tests/test_system_autonomy_permissions.py backend/tests/test_system_autonomy_state_machine.py backend/tests/test_system_autonomy_evidence.py backend/tests/test_system_autonomy_static_guard.py`

结果：

通过。

统计：

`14 passed in 0.04s`

## 14. 越界关键词检索结果

检索范围限制为：

1. `backend/zhifei_autoplan/system_autonomy_static_guard.py`
2. `backend/tests/test_system_autonomy_static_guard.py`
3. `docs/zdoc-system-autonomy-007-fix-1-static-guard-path-blocklist-correction-no-runtime.md`

检索结果：

1. 发现关键词命中。
2. 命中均位于授权 guard blocklist / command blocklist、授权测试样本和本 docs 的边界说明中。
3. 未发现本节点新增 `requests`、`FastAPI`、`APIRouter`、`open(`、runtime 启动、HTTP 客户端调用、endpoint 注册、subprocess 执行或文件正文读取逻辑。
4. `curl`、`localhost`、`ollama`、`prompt` 等命中属于既有命令静态 blocklist、授权测试样本或本 docs 负面确认，不代表本节点实际执行相关行为。

## 15. 是否修改测试文件

否。

## 16. 是否启动服务

否。

## 17. 是否访问 endpoint

否。

## 18. 是否运行 Ollama

否。

## 19. 是否模型推理

否。

## 20. 是否输入 prompt

否。

## 21. 是否读取真实 KG / 真实项目资料

否。

未读取真实 KG、真实项目资料、招标文件、图纸、清单或项目样本。

## 22. 是否读取 secrets / output / job / export / log 正文

否。

未读取 secrets、tokens、credentials、环境变量敏感信息、output、job、export、生成结果或日志正文。

## 23. 风险项

1. 本节点修复仍属于静态字符串守卫，不代表 runtime 链路已接入或运行时行为已验证。
2. path blocklist 为保守静态规则，后续如需扩大覆盖或降低误报，应在独立 Gate 中授权后处理。

## 24. 阻断项

未发现阻断项。

## 25. 回滚策略

如需回滚本节点，建议在后续明确授权后 revert 本节点提交。

本节点修改范围仅包含：

1. `backend/zhifei_autoplan/system_autonomy_static_guard.py`
2. `docs/zdoc-system-autonomy-007-fix-1-static-guard-path-blocklist-correction-no-runtime.md`

如本节点 tag 已创建且需回滚，应在后续明确授权后处理 tag。

## 26. 后续 Gate 建议

后续 Gate 原则上建议为：

`SYSTEM-AUTONOMY-007-REVALIDATION-1-STATIC-VALIDATION-ONLY-GATE`

但必须明确：

1. 本节点不得进入 revalidation。
2. revalidation 是否开启目标模式须由 ChatGPT 总控师审核后决定。
3. revalidation 默认禁止 runtime。
4. revalidation 默认禁止 endpoint。
5. revalidation 默认禁止 Ollama。
6. revalidation 默认禁止模型推理。
7. revalidation 默认禁止 prompt。
8. revalidation 默认禁止真实 KG / 真实项目资料。
9. revalidation 必须由 ChatGPT 总控师明确授权后才可执行。
