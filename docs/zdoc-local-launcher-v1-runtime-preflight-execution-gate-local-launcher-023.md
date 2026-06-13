# LOCAL-LAUNCHER-023 ZDoc Local App V1 Runtime Preflight Execution Gate

## 1. 节点名称

`LOCAL-LAUNCHER-023-ZDOC-LOCAL-APP-V1-RUNTIME-PREFLIGHT-EXECUTION-GATE`

## 2. 用户授权摘要

用户授权本节点执行 V1 runtime preflight execution。授权范围仅限仓库状态、分支、HEAD/tag、工作区 clean、非敏感目录结构、非敏感说明与 dependency manifest、非敏感启动命令文本、本地端口占用、本地进程状态、服务未运行状态、日志目录路径、配置模板、output/job/export 目录存在性、预检失败停止条件和 controlled start authorization 所需条件整理。

本节点不授权启动服务、停止服务、访问 endpoint、执行 curl/HTTP request、运行 Ollama、执行 `ollama list`、读取真实 KG、读取真实项目资料、读取真实招标文件、读取 `.env` / secrets / tokens / credentials、读取 registration / metadata / proof / manifest / sample 实例、读取 output/job/export 正文、触发 generation/export/write-back、进入 trial、进入真实使用、进入 50 人正式使用或进入 controlled start。

## 3. 当前基线 HEAD/tag

- 开始前 HEAD：`4c3f33c077be39cf0aded0bdc0a18b0ea0bf02b2`
- 开始前 tag：`v0.1.658-local-launcher-zdoc-local-app-v1-runtime-preflight-authorization-gate`
- 当前分支：`main`
- 上一节点：`LOCAL-LAUNCHER-022-ZDOC-LOCAL-APP-V1-RUNTIME-PREFLIGHT-AUTHORIZATION-GATE`

## 4. 实际执行命令清单

```bash
pwd
git status --short
git branch --show-current
git rev-parse HEAD
git tag --points-at HEAD
git log -1 --oneline
ls
find . -maxdepth 2 \( ...sensitive-prune... \) -prune -o -type d -print
find . -maxdepth 2 \( ...sensitive-prune... \) -prune -o -type f -print
find . -maxdepth 2 \( ...sensitive-prune... \) -prune -o -type f \( -name 'README.md' -o -name 'README.*' -o -name 'package.json' -o -name 'pnpm-lock.yaml' -o -name 'package-lock.json' -o -name 'yarn.lock' -o -name 'pyproject.toml' -o -name 'requirements.txt' -o -name 'requirements-dev.txt' -o -name 'setup.py' -o -name 'setup.cfg' -o -name 'Makefile' -o -name 'docker-compose.yml' -o -name 'compose.yml' \) -print
find local_launcher -maxdepth 2 \( ...sensitive-prune... \) -prune -o -type d -print
find local_launcher -maxdepth 2 \( ...sensitive-prune... \) -prune -o -type f -print
sed -n '1,180p' README.md
sed -n '1,160p' requirements.txt
sed -n '1,180p' local_launcher/v1/README.md
sed -n '1,160p' local_launcher/v0/README.md
lsof -nP -iTCP -sTCP:LISTEN
pgrep -fl "zdoc|vite|node|uvicorn|fastapi|python|flask|django|electron|tauri"
find . -maxdepth 2 \( ...sensitive-prune... \) -prune -o -type d -iname '*log*' -print
test -d logs
test -d output
test -d job
test -d export
find . -maxdepth 2 \( ...sensitive-prune... \) -prune -o -type f \( -iname '*template*' -o -iname '*.template' -o -iname '*.tpl' -o -iname '*.example' -o -iname '*config*.example' \) -print
find . -maxdepth 2 \( ...sensitive-prune... \) -prune -o -type d \( -iname '*template*' -o -iname '*config*' \) -print
git diff --check
git diff --cached --check
```

未执行 `npm install`、`npm run`、`yarn`、`pnpm`、`pip`、`python app.py`、`python main.py`、`uvicorn`、`flask`、`django`、`node server.js`、`vite`、`docker compose up`、`docker run`、`make`、`curl`、`wget`、`http`、`httpie`、`nc`、`telnet`、浏览器打开或任何 Ollama 命令。

## 5. 仓库路径检查结果

实际路径为：

```text
/Users/youfeini/Desktop/文档生成系统
```

结论：符合预期仓库路径。

## 6. 分支检查结果

实际分支：

```text
main
```

结论：符合预期分支。

## 7. HEAD/tag 检查结果

实际 HEAD：

```text
4c3f33c077be39cf0aded0bdc0a18b0ea0bf02b2
```

实际 HEAD tag：

```text
v0.1.658-local-launcher-zdoc-local-app-v1-runtime-preflight-authorization-gate
```

实际最近提交：

```text
4c3f33c LOCAL-LAUNCHER-022 runtime preflight authorization
```

结论：HEAD/tag 与 022 基线一致。

## 8. 工作区 clean 检查结果

开始预检时 `git status --short` 无输出。

结论：开始前工作区 clean。

## 9. 非敏感目录结构检查结果

已做 maxdepth 2 目录结构确认，并对 output/job/export、registration/metadata/proof/manifest/sample、`.env`、secret/token/credential/private/key、真实项目、招标、KG/知识图谱等敏感命名路径按敏感边界处理。

非敏感结构摘要：

- `docs/`
- `local_launcher/`
- `local_launcher/v1/`
- `local_launcher/v0/`
- `frontend/`
- `frontend_web/`
- `backend/`
- `app/`
- `api/`
- `routes/`
- `routers/`
- `scripts/`
- `tools/`
- `logs/`
- `build/`

边界说明：仓库中存在真实资料、知识图谱、sample/manifest 等高风险命名区域；本节点未读取这些目录或文件正文，后续 controlled start 前仍需继续保持 denylist。

## 10. 非敏感启动说明识别结果

识别并读取了以下非敏感说明文件：

- `README.md`
- `local_launcher/v1/README.md`
- `local_launcher/v0/README.md`

`local_launcher/v1/README.md` 明确说明 V1 当前是 professional static console only，不是可启动系统，不是 runtime preflight，不是 controlled start execution gate，也不是 trial 入口；不启动/停止 ZDoc 服务，不访问 endpoint，不运行 Ollama，不触发 generation/export/write-back，不包含可执行启动入口，不创建真正 App 包，不创建 runtime bridge。

## 11. 非敏感 manifest / dependency 文件识别结果

识别到：

- `requirements.txt`

未在允许范围内识别到：

- `package.json`
- `pnpm-lock.yaml`
- `package-lock.json`
- `yarn.lock`
- `pyproject.toml`
- `requirements-dev.txt`
- `setup.py`
- `setup.cfg`
- `Makefile`
- `docker-compose.yml`
- `compose.yml`

`requirements.txt` 仅作为 dependency manifest 读取，未执行 `pip` 或任何安装命令。

## 12. 非敏感启动命令文本识别结果

从 `README.md` 识别到以下启动/验证/生成相关文本，仅记录不执行：

- `pip3 install -r requirements.txt`
- `chmod +x scripts/run_e2e.sh`
- `./scripts/run_e2e.sh`
- `python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- `curl http://127.0.0.1:8000/health`
- `curl -X POST http://127.0.0.1:8000/compose ...`
- `curl -X POST http://127.0.0.1:8000/export -o output.docx`
- `curl http://127.0.0.1:8000/audit`
- `python3 backend/scripts/smoke_e2e.py`
- `python3 scripts/smoke_api.py`

从 `local_launcher/v1/README.md` 识别到：V1 不包含可执行启动入口、不包含可执行停止入口、不创建 runtime bridge。

结论：启动命令文本已识别；未执行任何启动、验证、生成、导出或 HTTP 命令。

## 13. 端口占用检查结果

执行：

```bash
lsof -nP -iTCP -sTCP:LISTEN
```

监听结果摘要：

- `rapportd`：`*:50265`、`*:64859`、`*:64860`
- `ControlCenter`：`*:7000`、`*:5000`
- `clash-verge`：`127.0.0.1:33331`

未发现 `uvicorn`、`fastapi`、`flask`、`django`、`vite`、`node server` 或 ZDoc 命名进程监听。未发现 README 中后端示例端口 `127.0.0.1:8000` 被监听。

结论：未发现疑似 ZDoc 后端或前端端口占用。

## 14. 进程状态检查结果

执行：

```bash
pgrep -fl "zdoc|vite|node|uvicorn|fastapi|python|flask|django|electron|tauri"
```

结果摘要：

- macOS `centaurid` / `AppleCentauri*` 命中 `tauri` 子串，判定为系统误命中。
- Codex MCP / `node_repl` 相关 `node` 进程存在，判定为 Codex 工具进程。
- 未发现 `zdoc`、`vite`、`uvicorn`、`fastapi`、`flask`、`django`、ZDoc 后端或 ZDoc 前端进程。

结论：未发现疑似 ZDoc 服务正在运行。

## 15. 服务未运行状态检查结果

- ZDoc 后端是否疑似运行：否。
- ZDoc 前端是否疑似运行：否。
- 是否发现 endpoint 访问行为：否。
- 是否发现 Ollama 命令执行：否。

结论：服务未运行状态检查完成。

## 16. 日志目录路径识别结果

执行：

```bash
test -d logs
find . -maxdepth 2 \( ...sensitive-prune... \) -prune -o -type d -iname '*log*' -print
```

识别到：

- `logs/`
- `.git/logs`

仅识别路径，未读取任何日志正文。

## 17. 配置模板识别结果

识别到以下非敏感模板命名路径，仅记录路径，未读取正文：

- `frontend_web/w6_template_editor.html`
- `frontend_web/w6_template_default.json`
- `frontend_web/templates`
- `projects/_template`

未读取 `.env`、`.env.*`、secrets、tokens、credentials 或 private key。

## 18. output/job/export 目录存在性识别结果

按精确目录名执行：

```bash
test -d output
test -d job
test -d export
```

结果：

- `output/`：不存在。
- `job/`：不存在。
- `export/`：不存在。

未读取 output/job/export 正文，未写入 output/job/export。

## 19. 禁止事项复核

- 未修改 V1 页面产物。
- 未修改 V0。
- 未修改 backend/frontend/config/dependency。
- 未新增 JS 文件。
- 未创建脚本。
- 未创建真正 App 包。
- 未运行 npm/yarn/pnpm/pip。
- 未运行测试/lint/build。
- 未打开 HTML 页面。
- 未启动服务。
- 未停止服务。
- 未访问 endpoint。
- 未执行 curl / HTTP request。
- 未运行 Ollama。
- 未执行 `ollama list`。
- 未读取真实 KG 正文。
- 未读取真实项目资料正文。
- 未读取真实招标文件正文。
- 未读取 `.env` / secrets / tokens / credentials。
- 未读取 registration / metadata / proof / manifest / sample 实例正文。
- 未读取 output/job/export 正文。
- 未触发 generation/export/write-back。
- 未写 output/job/export。
- 未进入 trial。
- 未进入真实使用。
- 未进入 50 人正式使用。
- 未进入 controlled start。
- 未进入 `LOCAL-LAUNCHER-024`。

## 20. 预检失败停止条件

后续如出现以下任一情况，必须停止并不得进入 controlled start：

- 工作区不 clean。
- HEAD/tag 与授权基线不一致。
- 发现疑似 ZDoc 服务已运行。
- 发现关键端口被疑似 ZDoc 进程占用。
- 无法确认启动命令边界。
- 发现 `.env` / secrets / tokens / credentials 误读风险。
- 发现真实 KG / 真实项目资料 / 真实招标文件误读风险。
- 发现 output/job/export 正文读取或写入风险。
- 需要启动服务、访问 endpoint、运行 Ollama、执行生成/导出/写回、进入 trial 或真实使用。

## 21. controlled start authorization 前置条件

进入 `LOCAL-LAUNCHER-024-ZDOC-LOCAL-APP-V1-CONTROLLED-START-AUTHORIZATION-GATE` 前，至少需要单独授权并明确：

- 允许启动的具体服务命令。
- 后端/前端归属与工作目录。
- 允许监听的端口。
- 日志写入路径和允许读取范围。
- 停止/回滚方式。
- 健康检查 endpoint 是否允许访问。
- 是否允许读取配置模板以及严格禁止读取 `.env`/secrets 的方式。
- 是否仍禁止 Ollama、trial、generation、export、write-back。
- 服务启动后的最小验证项和停止条件。

## 22. PASS 判定

`LOCAL-LAUNCHER-023 ZDOC LOCAL APP V1 RUNTIME PREFLIGHT EXECUTION GATE PASSED / RUNTIME PREFLIGHT COMPLETED / CONTROLLED START AUTHORIZATION MAY BE CONSIDERED / NO SERVICE STARTED / NO ENDPOINT ACCESSED / NO OLLAMA RUN / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`

判定依据：

- 仓库在预期路径。
- 分支为 `main`。
- HEAD/tag 与 022 基线一致。
- 开始前工作区 clean。
- 未发现疑似 ZDoc 服务已运行。
- 未访问 endpoint。
- 未运行 Ollama。
- 未读取真实 KG / 真实项目资料 / 真实招标文件正文。
- 未读取 `.env` / secrets / tokens / credentials。
- 未读取 output/job/export 正文。
- 未触发 generation/export/write-back。
- 未进入 trial。
- 未进入 controlled start。

## 23. 下一节点建议

可以考虑进入 `LOCAL-LAUNCHER-024-ZDOC-LOCAL-APP-V1-CONTROLLED-START-AUTHORIZATION-GATE` 的授权评审，但本节点未进入 024。

下一节点不得自动执行；必须由用户另行明确授权。
