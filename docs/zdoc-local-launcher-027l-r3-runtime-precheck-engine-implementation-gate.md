# LOCAL-LAUNCHER-027L-R3-RUNTIME-PRECHECK-ENGINE-IMPLEMENTATION-GATE

## 1. 节点名称

LOCAL-LAUNCHER-027L-R3-RUNTIME-PRECHECK-ENGINE-IMPLEMENTATION-GATE

## 2. 基线 commit

* baseline commit：`e280332751a1edac67e5ab3ac1d7f8fbd023a25c`
* baseline commit message：`docs: archive local launcher 027k full stack start result`
* baseline tag：`v0.1.714-local-launcher-027k-post-merge-main-baseline`

## 3. 当前节点性质

本节点为执行层落地节点，将 027L 运行态治理设计转化为静态 Python 预检引擎与归档文档。

本节点不启动服务，不访问 localhost，不读取 runtime/PID/log，不触发 Ollama 或模型推理。

## 4. 允许变更范围

仅新增以下范围：

* `runtime_governance/`
* `runtime_governance/precheck/`
* `runtime_governance/precheck/rules/`
* `docs/zdoc-local-launcher-027l-r3-runtime-precheck-engine-implementation-gate.md`

## 5. 新增代码结构

```text
runtime_governance/
  __init__.py
  precheck/
    __init__.py
    models.py
    result.py
    engine.py
    evaluator.py
    rules/
      __init__.py
      git_rules.py
      runtime_rules.py
      port_rules.py
      process_rules.py
      lock_rules.py
```

## 6. PrecheckContext 字段说明

`PrecheckContext` 是纯输入上下文，字段包括：

* `repo_path`
* `branch`
* `head`
* `origin_head`
* `head_tree`
* `origin_tree`
* `working_tree_clean`
* `expected_head`
* `expected_tree`
* `expected_tag`
* `local_tag_target`
* `remote_tag_target`
* `ports`
* `processes`
* `runtime_locks`
* `allow_conditional_cleanup`

`from_dict` 用于从 dict 安全构造上下文。

## 7. Decision 判定规则

`Decision` 包含：

* `ALLOW`
* `BLOCK`
* `CONDITIONAL`

引擎初始分为 100，叠加所有 `RuleOutcome.score_delta` 后限制在 0 到 100。

* 任一规则 `hard_block=True`：`BLOCK`
* 无 hard block 且 score >= 85：`ALLOW`
* 无 hard block 且 60 <= score < 85：`CONDITIONAL`
* score < 60：`BLOCK`

## 8. Hard Block 规则

以下情况会形成 hard block：

* Git 基线不一致。
* 工作区不 clean。
* 027K tag 指向不一致。
* 必需进程状态键缺失。
* 未授权清理时发现 uvicorn、streamlit、ollama 已运行。
* 必需端口状态键缺失。
* 未授权清理时发现 8010 或 8501 非 free。
* 必需 runtime lock 状态键缺失。
* 未授权清理时发现 PID/log/runtime lock。
* 未授权清理时发现未知受控进程标记为 True。

## 9. Conditional 规则

当 `allow_conditional_cleanup=True` 且不存在缺失的必需上下文字段时，以下状态可进入 `CONDITIONAL` 并输出 actions：

* 受控运行进程已存在。
* 8010 或 8501 非 free。
* runtime/PID/log lock 已存在。
* 未知受控进程标记为 True。

## 10. 运行态禁触说明

本实现仅基于传入 context 做纯逻辑判断。

代码不执行 shell 命令，不访问网络，不访问 localhost，不真实扫描端口，不真实检查进程，不读取 runtime/PID/log，不启动 uvicorn、streamlit、Ollama 或后台进程。

## 11. 静态校验结果

本节点要求执行：

* `python3 -m compileall runtime_governance`
* 纯 Python 内存场景校验，预期 `Decision.ALLOW`
* `git diff --check`

校验结果以本节点最终回报为准。

## 12. 禁止事项确认

本节点禁止：

* 直接 push main。
* 合并 PR。
* force push。
* push tags/all/mirror。
* 创建、删除、覆盖或移动 tag。
* 修改 027K 归档文档。
* 修改 ruleset 或 branch protection。
* 启动 uvicorn、streamlit、Ollama。
* 访问 localhost 或 127.0.0.1。
* 读取、写入、删除 runtime/PID/log。
* 运行项目测试套件、构建或安装依赖。

## 13. 后续建议节点

`LOCAL-LAUNCHER-027L-R4-RUNTIME-PRECHECK-ENGINE-PR-REVIEW-GATE`
