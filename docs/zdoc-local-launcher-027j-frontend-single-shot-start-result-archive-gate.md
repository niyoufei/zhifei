# LOCAL-LAUNCHER-027J-INDEPENDENT-RUNTIME-FRONTEND-SINGLE-SHOT-START-RESULT-ARCHIVE-GATE

## 1. 节点背景

027G 已完成 post-merge main baseline 封口，当前 main 基线为 `eab0700c0688ac3d6cd87229af8df368f92fa6fd`。

027H 完成前端只读预检后，027I 进入 frontend-only 单次受控启动链。027I 原节点使用普通后台方式启动后，PID 在归属验证前退出；D1A 随后进行最小静态诊断；027I-R1 使用 `nohup` 进行单次重试但仍阻断；027I-R2 改用 Python 监督脚本和 `subprocess.Popen`，完成前端受控启动、Streamlit health 校验和停止回收。

本 027J 节点仅归档该治理链结果。它不启动服务，不访问 localhost，不读取或写入 runtime、PID、log 文件，不修改源码、配置或脚本。

## 2. 基线状态

* 仓库路径：`/Users/youfeini/Desktop/文档生成系统`
* 分支：`main`
* main HEAD：`eab0700c0688ac3d6cd87229af8df368f92fa6fd`
* origin/main HEAD：`eab0700c0688ac3d6cd87229af8df368f92fa6fd`
* tag：`v0.1.712-local-launcher-027g-post-merge-main-baseline`
* 工作区状态：clean
* GitHub main 保护状态：本节点不修改 branch protection、repository ruleset 或 lock_branch。

## 3. 027I 原节点阻断说明

027I 原节点执行了一次 frontend-only 启动，启动方式为普通后台方式。

* PID：`75668`
* 阻断原因：PID 在归属验证前退出
* health：未进入成功判定
* log：`logs/webui_frontend.027i.20260628T193228.log`
* log 大小：`0 bytes`
* backend / watcher / Ollama / launcher：均未触发

该阻断更符合启动策略或进程保持问题，不直接定性为前端代码失败。

## 4. D1A 最小诊断结果

D1A 作为 027I 阻断后的最小诊断审计节点，仅做只读诊断。

* Python：`Python 3.13.3`
* Python 路径：`/usr/local/bin/python3`
* Streamlit：`1.54.0`
* Streamlit 可导入：是
* `app.py` 未发现 `sys.exit` / `os._exit`
* 未发现明显 import-time 退出风险
* `.streamlit/config.toml` 与 027I 命令参数无冲突
* `scripts/run_web_ui.sh` 存在 `nohup` + `/dev/null` + stdout/stderr 日志 + PID 写入的较稳定后台保持方式
* 仍禁止直接使用组合 launcher

D1A 结论：027I 原节点即退更可能与后台进程保持方式或 Codex 执行器回收有关。

## 5. 027I-R1 重试结果

027I-R1 授权使用 `nohup` 进行一次 frontend-only 重试。

* 启动方式：`nohup` frontend-only
* PID：`63612`
* 阻断原因：PID 在第一次 3 秒延迟归属验证前退出
* log：`logs/webui_frontend.027i-r1.20260628T210208.log`
* log 大小：`0 bytes`
* health：未进入成功判定
* backend：未启动
* launcher / watchdog / Ollama / 业务接口：均未触发

R1 阻断后，不再继续使用普通后台或 `nohup` 方式作为该受控前端验证链的启动策略。

## 6. 027I-R2 监督启动结果

027I-R2 改用前台 Python 监督脚本，通过 `subprocess.Popen` 启动一次 Streamlit 子进程，并由监督脚本负责 PID 记录、日志捕获、health 检查和受控停止。

* 启动方式：Python 监督脚本 + `subprocess.Popen`
* 前端入口：`app.py`
* 命令摘要：`python3 -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --server.fileWatcherType none --server.runOnSave false`
* 子进程 PID：`74854`
* 3 秒后子进程仍存在：是
* log：`logs/webui_frontend.027i-r2.20260628T210856.log`
* log 大小：`101 bytes`
* log 摘要：Streamlit 输出可查看 URL `http://127.0.0.1:8501`，随后 `Stopping...`
* 仅启动 frontend：是
* backend：未启动
* `.app`：未使用
* `run_web_ui.sh` / `start_web_ui_background.sh`：未使用
* watchdog：未启动
* Ollama：未启动
* 模型推理：未触发

## 7. Streamlit health 结果

027I-R2 仅访问授权 Streamlit health URL。

* URL：`http://127.0.0.1:8501/_stcore/health`
* HTTP 状态码：`200`
* 响应摘要：`ok`
* 根页面 `/`：未访问
* backend：未访问
* 非 health 路由：未访问
* 业务接口：未触发
* Ollama / 模型推理：未触发

该结果证明 frontend-only 单次受控启动后，Streamlit health 可以在授权边界内返回正常状态。

## 8. 停止与回收结果

027I-R2 在 health 完成后执行受控停止和回收。

* terminate：是
* kill：否
* PID 是否退出：是
* PID 文件是否删除：是
* log 是否保留：是
* 停止后 8501 health：connection refused
* 残留前端进程：未发现本节点 PID 残留

停止回收闭合，未发现未授权运行态残留。

## 9. 边界保持结论

027J 仅新增本归档文档。

* 未修改源码 / 配置 / 脚本
* 未修改 README 或既有治理文档
* 未修改 `.gitignore`
* 未启动服务
* 未访问 localhost
* 未访问 Streamlit health 或根页面
* 未访问 backend
* 未触碰 runtime / PID / log
* 未读取真实密钥
* 未运行测试 / 构建 / 安装
* 未启动 watchdog、Ollama 或模型推理
* 未修改 GitHub protection / ruleset
* 工作区在归档前后保持可审计状态

## 10. 总控结论

027I-R2 已通过。前端 frontend-only 单次受控启动能力已验证，Streamlit health 可用，Python 监督脚本方式是后续受控前端验证的优先策略。

本链路已完成停止回收闭合，无未授权运行态残留。

建议下一节点进入：

`LOCAL-LAUNCHER-027K-INDEPENDENT-RUNTIME-FULL-STACK-PREFLIGHT-AUDIT`

或由总控另行指定。
