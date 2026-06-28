# LOCAL-LAUNCHER-027G-INDEPENDENT-RUNTIME-BACKEND-SINGLE-SHOT-START-RESULT-ARCHIVE-GATE

## 1. 节点背景

027D 已封口，main 基线为 `2631632bb10d679623d34efefe1eee3da9c0e876`。027E 已完成 backend-only 单次启动前的只读预检，确认后端入口为 `backend/app/main.py`，FastAPI app 为 `backend.app.main:app`。

027F 原节点因“只能启动一次”的节点规则被消耗而形成治理阻断。027F-R1 作为重新授权节点执行，目标是在不触发前端、`.app`、Streamlit、watchdog、Ollama 或模型推理的前提下，完成后端单次受控启动、`/health` 校验、受控停止和状态回收。

## 2. 基线状态

* 仓库路径：`/Users/youfeini/Desktop/文档生成系统`
* 分支：`main`
* main HEAD：`2631632bb10d679623d34efefe1eee3da9c0e876`
* origin/main HEAD：`2631632bb10d679623d34efefe1eee3da9c0e876`
* tag：`v0.1.711-local-launcher-027d-post-merge-main-baseline`
* 工作区状态：clean
* GitHub main 保护状态：不在本节点修改

## 3. 027F 原节点阻断说明

* 原 027F 已消耗单次启动机会。
* Codex 未在原节点内违规重试。
* PID 文件不存在。
* 工作区 clean。
* log 文件存在但上一轮尾部为空。
* 该阻断属于治理规则阻断，不定性为代码失败。

## 4. 027F-R1 重试授权范围

* backend-only。
* 仅端口 `8010`。
* 仅 `/health`。
* 仅授权 PID / log 路径。
* 禁止前端。
* 禁止 `.app`。
* 禁止 Streamlit。
* 禁止 watchdog。
* 禁止 Ollama。
* 禁止模型推理。
* 禁止真实密钥读取或打印。

## 5. 027F-R1 启动结果

* Python 版本：`Python 3.13.3`
* uvicorn 模块：found
* fastapi 模块：found
* 启动命令摘要：`python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8010`
* PID：`61127`
* PID 归属验证：通过
* 第二次启动：否
* 前端 / Streamlit / watchdog / Ollama / model 触发：否

## 6. 健康检查结果

* URL：`http://127.0.0.1:8010/health`
* HTTP 状态码：`200`
* 响应摘要：`ok=true`、`service=文档生成系统`、`system_id=docgen-system`、`audit_ready=true`
* system_id 校验：通过
* 非授权路由触发：否
* Ollama / 模型推理触发：否

## 7. 停止与回收结果

* 停止 PID：`61127`
* 停止前 PID 归属验证：通过
* TERM：是
* KILL：否
* PID 是否退出：是
* PID 文件是否删除：是
* log 是否保留：是
* 停止后 `/health`：连接拒绝
* 残留后端进程：无本节点 PID 残留

## 8. 边界保持结论

* 027G 仅新增本归档文档。
* 未修改源码 / 配置。
* 未修改脚本。
* 未修改既有文档。
* 未修改 README。
* 未修改既有治理文档。
* 未启动前端。
* 未启动 Streamlit。
* 未启动 watchdog。
* 未启动 Ollama。
* 未访问非 `/health` 路由。
* 未运行 curl / lsof / open。
* 未运行测试 / 构建 / 安装。
* 未读取或打印真实密钥。
* 工作区 clean。

## 9. 总控结论

* 027F-R1 已通过。
* 后端 backend-only 单次启动能力已验证。
* 后端 `/health` 可用。
* 停止回收闭合。
* 无未授权运行态残留。
* 建议下一节点进入：
  `LOCAL-LAUNCHER-027H-INDEPENDENT-RUNTIME-FRONTEND-PREFLIGHT-AUDIT`
  或由总控另行指定。
