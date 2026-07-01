# LOCAL-LAUNCHER-027K-R2-INDEPENDENT-RUNTIME-FULL-STACK-RESULT-ARCHIVE-GATE

## 1. 节点性质

本文件用于归档 LOCAL-LAUNCHER-027K-R1-INDEPENDENT-RUNTIME-FULL-STACK-SINGLE-SHOT-START-GATE 的 full-stack health-only 单次受控启动验证结果。

本次验证目标为确认 backend 与 frontend 能够按受控顺序启动、通过 health-only 验证、按受控顺序停止，并在停止后释放端口。

## 2. 基线信息

* 目标仓库：/Users/youfeini/Desktop/文档生成系统
* 当前分支：local-launcher-027j-frontend-single-shot-start-result-archive-gate
* 当前 HEAD：19bde4366ea91457d5cbf3466312197971c548a2
* 当前 HEAD tree：cd8275067b75fd043ad0dead4cbeb18645ea6d8c
* origin/main HEAD：7c09062f99f66935246080e5379c6981d5abefde
* origin/main tree：cd8275067b75fd043ad0dead4cbeb18645ea6d8c
* 027J tag：v0.1.713-local-launcher-027j-post-merge-main-baseline
* 027J tag 指向：7c09062f99f66935246080e5379c6981d5abefde
* 工作区启动前状态：clean

## 3. 启动策略

本次 full-stack 验证采用 Python 监督脚本管控，不使用后台脚本，不使用 .app，不访问 Streamlit 根页面，不访问 backend 业务接口，不触发 Ollama 或模型推理。

启动顺序为：

1. 预检 127.0.0.1:8010 端口空闲；
2. 预检 127.0.0.1:8501 端口空闲；
3. 通过 subprocess.Popen 启动 backend；
4. 仅访问 backend health URL；
5. backend health 通过后，通过 subprocess.Popen 启动 frontend；
6. 仅访问 frontend health URL；
7. 先 terminate frontend；
8. 再 terminate backend；
9. 停止后复核 8010、8501 端口释放。

## 4. backend 验证结果

* backend 启动命令：python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8010
* backend PID：80032
* backend health URL：http://127.0.0.1:8010/health
* backend health 状态码：200
* backend health 响应摘要：包含 "ok":true、"system_id":"docgen-system"
* backend 停止方式：TERM
* backend 是否使用 kill：NO
* 停止后 8010 是否释放：YES

## 5. frontend 验证结果

* frontend 启动命令：python3 -m streamlit run app.py --server.address=127.0.0.1 --server.port=8501 --server.headless=true --browser.gatherUsageStats=false
* frontend PID：80035
* frontend health URL：http://127.0.0.1:8501/_stcore/health
* frontend health 状态码：200
* frontend health 响应摘要：ok
* frontend 停止方式：TERM
* frontend 是否使用 kill：NO
* 停止后 8501 是否释放：YES

## 6. 禁止边界执行情况

* 是否访问 Streamlit 根页面：NO
* 是否访问 backend 业务接口：NO
* 是否触发 Ollama / 模型推理：NO
* 是否读取/写入 runtime/PID/log：NO
* 是否发生 git 写操作：NO
* 是否执行 fetch/pull/switch/checkout：NO
* 是否运行 curl/lsof/open/.app：NO
* 是否运行 run_web_ui.sh/start_web_ui_background.sh/stop_web_ui_background.sh：NO
* 是否运行测试/构建/安装：NO

## 7. 停止与残留复核

* frontend 停止方式：TERM
* backend 停止方式：TERM
* 是否使用 kill：NO
* 停止后 8010 是否释放：YES
* 停止后 8501 是否释放：YES
* 工作区结束后是否 clean：YES
* 是否存在未授权运行态残留：NO

## 8. 风险等级

风险等级：LOW

原因：本次 full-stack 验证仅访问 backend /health 与 Streamlit _stcore/health，未访问根页面、业务接口、Ollama 或模型推理；backend 与 frontend 均通过 TERM 受控停止，端口释放完成，未形成运行态残留。

## 9. 验收结论

LOCAL-LAUNCHER-027K-R1-INDEPENDENT-RUNTIME-FULL-STACK-SINGLE-SHOT-START-GATE 验证结果为 PASS。

允许进入后续 027K-R2 归档 PR 审查流程，但不得自动进入后续运行态节点。
