# 文档生成系统域名接入

适用场景：
- Cloudflare 已将 `doc` 子域名指向服务器公网 IP
- 服务器本机运行 FastAPI `127.0.0.1:8010`
- 服务器本机运行 Streamlit `127.0.0.1:8501`

接入步骤：

1. 后端服务

使用 [docgen-autoplan.service](/Users/youfeini/Desktop/文档生成系统/deploy/systemd/docgen-autoplan.service) 启动后端，默认监听 `127.0.0.1:8010`。

当前生产建议默认采用“单 service”形态：

- `docgen-autoplan.service` 持有后端
- 同时由其内部自愈/编排链维护 `127.0.0.1:8501` 的 Streamlit 子进程

这也是当前 `doc.niyoufei.com` 现网已经验证通过的运行方式。

2. Web UI 服务

[docgen-streamlit.service](/Users/youfeini/Desktop/文档生成系统/deploy/systemd/docgen-streamlit.service) 仅作为可选的独立 Streamlit unit 保留。

默认不要启用它；只有在你的源站没有后端自带的 Web UI 拉起链时，才考虑单独启用。

如果同时启用：

- `docgen-autoplan.service`
- `docgen-streamlit.service`

在当前这套栈上会造成 `8501` 端口争抢。

3. Nginx 反向代理

将 [docgen-streamlit-origin.conf.template](/Users/youfeini/Desktop/文档生成系统/deploy/nginx/docgen-streamlit-origin.conf.template) 中的 `__DOCGEN_DOMAIN__` 替换为真实完整域名，例如 `doc.niyoufei.com`，再放到 Nginx `sites-enabled`。

如果 Cloudflare SSL 模式是 `Full` 或 `Full (strict)`，则应改用 [docgen-streamlit-origin-ssl.conf.template](/Users/youfeini/Desktop/文档生成系统/deploy/nginx/docgen-streamlit-origin-ssl.conf.template)，并提供源站证书路径：

```bash
export DOCGEN_SSL_CERT=/etc/ssl/certs/doc-origin.pem
export DOCGEN_SSL_KEY=/etc/ssl/private/doc-origin.key
```

如果你已经在 Linux 源站机器上放好了本仓库，也可以直接执行：

```bash
sudo ./scripts/install_linux_domain_origin.sh doc.niyoufei.com
```

如果你当前还不能从本机 SSH 到源站，也可以先在本地渲染一份可上传的部署 bundle：

```bash
bash ./scripts/render_linux_domain_bundle.sh doc.niyoufei.com
```

默认输出目录：

```bash
build/domain_bundle/doc.niyoufei.com.nginx/
```

其中会包含：
- `docgen-autoplan.service`
- `docgen-streamlit.service`
- `docgen-streamlit-origin.conf`
- `README.txt`
- `install_bundle_on_origin.sh`
- `detect_linux_proxy_stack.sh`
- `suggest_linux_origin_fix.sh`
- `generate_origin_tls_csr.sh`
- `verify_linux_domain_origin.sh`

如果同时设置了 `DOCGEN_SSL_CERT` 和 `DOCGEN_SSL_KEY`，渲染出的 Nginx 配置会自动切换到 443 源站模板。

如果你希望直接得到一个可上传的压缩包，可以运行：

```bash
bash ./scripts/package_linux_domain_bundle.sh doc.niyoufei.com
```

默认会生成：

```bash
build/domain_bundle_release/doc.niyoufei.com.nginx.tar.gz
build/domain_bundle_release/doc.niyoufei.com.nginx.tar.gz.sha256
build/domain_bundle_release/doc.niyoufei.com.nginx.upload.txt
```

其中：
- 文件名会带上当前 `DOCGEN_PROXY_STACK`
- bundle 目录名也会带上当前 `DOCGEN_PROXY_STACK`
- `upload.txt` 会给出对应栈的源站解压和安装命令

如果 SSH 已经可用，也可以直接本机上传并在源站执行安装：

```bash
bash ./scripts/push_linux_domain_bundle.sh doc.niyoufei.com root@199.180.118.204
```

如只想预览将要执行的上传与远端安装命令：

```bash
DOCGEN_PREVIEW=1 bash ./scripts/push_linux_domain_bundle.sh doc.niyoufei.com root@199.180.118.204
```

如只上传不安装：

```bash
DOCGEN_REMOTE_INSTALL=0 bash ./scripts/push_linux_domain_bundle.sh doc.niyoufei.com root@199.180.118.204
```

源站安装完成后，可在服务器本机执行：

```bash
bash ./verify_linux_domain_origin.sh doc.niyoufei.com
```

它会检查：
- `docgen-autoplan.service` 是否 `active`
- `docgen-streamlit.service` 是否处于可接受状态
- `nginx -t` 是否通过
- `ssl_certificate` 文件是否存在，以及是否覆盖目标域名
- `127.0.0.1:8010/health`
- `127.0.0.1:8501/_stcore/health`
- 本机携带 `Host/SNI` 的 80/443 命中结果
- 可选 OCR 运行时：
  - `tesseract` 是否已安装
  - `ocr_runtime` 是否识别到可用 OCR 引擎
  - 可选中文语言包是否可用

如果你确实要验证“独立 Streamlit unit 必须 active”，可显式设置：

```bash
DOCGEN_EXPECT_STREAMLIT_SERVICE=1 bash ./verify_linux_domain_origin.sh doc.niyoufei.com
```

如果这台源站需要处理扫描件 / 图片 OCR，可显式开启 OCR 验收：

```bash
DOCGEN_EXPECT_OCR=1 DOCGEN_EXPECT_OCR_CHINESE=1 bash ./verify_linux_domain_origin.sh doc.niyoufei.com
```

如果源站实际是 `xray -> nginx fallback` 或其它不直接监听 `80/443` 的拓扑，可同时跳过本机 `Host/SNI` 直连检查：

```bash
DOCGEN_EXPECT_OCR=1 DOCGEN_EXPECT_OCR_CHINESE=1 DOCGEN_SKIP_PROXY_HOST_CHECK=1 bash ./verify_linux_domain_origin.sh doc.niyoufei.com
```

如果只想单独确认 OCR 运行时，而不混合其它源站门禁，可直接运行：

```bash
DOCGEN_EXPECT_OCR_CHINESE=1 bash ./verify_ocr_runtime.sh
```

它会单独检查：
- `.venv/bin/python` 是否可用
- `tesseract` 是否可执行
- 语言包列表是否可读
- `ocr_runtime` 是否识别到正确默认语言
- 用临时 PDF 跑一次真实 OCR smoke

如果要把“文件选择 -> 上传 -> 解析 -> 计划存取”这条主链一次性跑通，可直接运行：

```bash
bash ./verify_upload_parse_chain.sh
```

它会：
- 生成或复用最小冒烟样本 `tender.docx` / `boq.xlsx` / `drawing.png`
- 验证 `/ingest/upload` 能正确落到 `word/excel/image` 解析链
- 验证 `/actions/tender/parse`、`/actions/boq/parse`
- 验证 `/actions/plan/save`、`/actions/plan/get`
- 检查返回的 `saved_at` / `preview_saved_as` 等路径是否真实存在

注意：
- 该脚本会写入少量 `backend/data/uploads`、`backend/data/extracts`、`backend/data/previews`、`backend/data/audit`、`backend/data/autoplan/projects` 冒烟记录
- 如需复用现成样本，可设置 `DOCGEN_UPLOAD_PARSE_FIXTURE_DIR=/your/fixtures`

如果要继续验证“异步生成 -> 轮询 -> 结果读取 -> 下载导出”这条后半段主链，可直接运行：

```bash
bash ./verify_generate_export_chain.sh
```

它会：
- 生成或复用最小 `tender.docx` / `boq.xlsx` 样本
- 用 `dry_run` 调 `run_actions_pipeline.py`
- 验证 `/actions/generate_async`
- 验证 `/actions/job_status`
- 验证 `/actions/result`
- 验证 `/actions/download`
- 检查下载到 `build/actions_runs/<job_id>/` 的核心产物是否真实存在

注意：
- 该脚本会写入少量 `jobs`、`build/actions_runs`、`build/actions_*.json/docx` 冒烟记录
- 默认走 `dry_run`，不会发起真实高成本模型生成

如果你需要在真实浏览器层确认“文件选择 -> 页面摘要更新 -> 从评审标准载入目录”这条前半链路，可运行：

```bash
DOCGEN_UI_BASE_URL=http://127.0.0.1:18501 bash ./scripts/verify_ui_upload_outline_chain.sh
```

如果你要直接从本机对远端源站做这一轮 UI 验证，而不想手工维护 SSH 隧道，优先运行：

```bash
bash ./scripts/verify_remote_ui_upload_outline_chain.sh root@199.180.118.204
```

如果你要从本机一次性串行检查：
- 远端 UI 前半链路
- 源站运行健康
- 上传解析链
- 生成导出链

可直接运行：

```bash
bash ./scripts/verify_remote_full_chain.sh root@199.180.118.204
```

默认会把每个步骤的原始输出落到：

```bash
output/smoke_logs/remote_full_chain/<timestamp>/
```

它会：
- 打开指定 UI 地址
- 用 Playwright 直接把最小 `tender.docx` / `boq.xlsx` 填进前两个上传控件
- 验证页面摘要变成 `已选文件：招标/答疑 1 · 清单 1`
- 点击“从评审标准载入目录”
- 验证页面不再停留在“目录为空”，且已经渲染出章节条目
- 检查浏览器网络里存在 `PUT /_stcore/upload_file ... => 204`

注意：
- `verify_ui_upload_outline_chain.sh` 现在支持双 runner：
  - 若本机 Python 已安装 `playwright`，默认优先走 Python runner
  - 若未安装，则回退到 `node` 与 npx 缓存中的 `playwright-core`
  - 两种模式都要求可执行的 Chrome 浏览器
- `verify_remote_ui_upload_outline_chain.sh` 会临时建立 `ssh -L 18501:127.0.0.1:8501` 隧道，再调用上述本地浏览器 smoke
- `verify_remote_full_chain.sh` 会在远端继续调用 `verify_upload_parse_chain.sh` 与 `verify_generate_export_chain.sh`，因此会写入少量线上 smoke 记录；只应在允许的运维窗口执行
- 推荐优先对本地 `http://127.0.0.1:8501` 或 SSH 隧道地址执行；若直接打公网域名，Cloudflare 静态资源抖动可能干扰浏览器结论
- 该脚本只验证 UI 前半链路，不会点击“一键生成”，因此不会触发真实模型生成

如果你需要在本机对“admin 只读运维链”做隔离 smoke，而不想改动当前常驻 `8010/8501`，可直接运行：

```bash
bash ./scripts/verify_local_admin_ops_api.sh
bash ./scripts/verify_local_admin_ops_panel.sh
bash ./scripts/verify_local_admin_ops_chain.sh
bash ./scripts/verify_local_ui_admin_chain.sh
```

其中：

- `verify_local_admin_ops_api.sh` 会在临时端口启动一份 FastAPI，运行时随机生成 `ZF_ADMIN_KEY`，并验证 `/auth/tenant_usage_reports*` 只读接口
- `verify_local_admin_ops_panel.sh` 会在临时端口启动 FastAPI + Streamlit，注入临时 `ZF_ADMIN_KEY`，并用浏览器实际验证“维护 / 诊断（开发） -> 运营管理台（只读） -> 刷新管理台”
- `verify_local_ui_admin_chain.sh` 会串行调用：
  - `verify_ui_upload_outline_chain.sh`
  - `verify_local_admin_ops_chain.sh`
  适合作为本机浏览器运维基线入口
- `verify_local_admin_ops_chain.sh` 会串行调用前两条 admin 本地 smoke，并把每一步原始日志收口到：

其中 `verify_local_admin_ops_chain.sh` 会把每一步原始日志收口到：

```bash
output/smoke_logs/local_admin_ops_chain/<timestamp>/
```

`verify_local_ui_admin_chain.sh` 则会把日志落到：

```bash
output/smoke_logs/local_ui_admin_chain/<timestamp>/
```

注意：

- 这四条脚本都是“本地运维基线工具”，不属于服务器 release/worktree 工具，不会写入 `latest-release-ops.txt`
- 默认使用隔离端口：
  - API smoke：`18010`
  - admin 面板 smoke：backend `18012`、web `18512`
- `verify_local_ui_admin_chain.sh` 为避免与单独 admin smoke 撞端口，默认改用：
  - admin API：`18110`
  - admin 面板：backend `18112`、web `18612`
- `ZF_ADMIN_KEY` 仅在脚本运行时注入到临时进程，不会写入仓库、`.env` 或 `.runtime/local_keys.env`
- `verify_local_admin_ops_panel.sh` 默认使用本机 Python Playwright；若你要切到 node runner，可设置 `DOCGEN_ADMIN_UI_SMOKE_BROWSER_IMPL=node`
- `verify_local_ui_admin_chain.sh` 依赖本地 `http://127.0.0.1:8501` 可访问；它默认把 `verify_ui_upload_outline_chain.sh` 切到 Python runner，若要强制改回 node，可设置 `DOCGEN_LOCAL_UI_BROWSER_IMPL=node`
- 这组脚本只验证本地浏览器与只读 admin 成功路径，不会触发任何 execute/delete 类清理动作
- 如果你只想预览将要启动的临时端口和命令，可统一加 `DOCGEN_PREVIEW=1`

如果你需要把应用代码整体打成服务器部署包，而不是手工排除目录，可直接运行：

```bash
bash ./scripts/package_docgen_server_app.sh
```

如果你已经在本地生成了最新 release，并且只想把它同步到服务器 `/opt/docgen/releases`，可直接运行：

```bash
bash ./scripts/push_docgen_server_release.sh root@199.180.118.204
```

如果你只想先看将要执行的 `scp/ssh` 命令，不真正写服务器，可运行：

```bash
DOCGEN_PREVIEW=1 bash ./scripts/push_docgen_server_release.sh root@199.180.118.204
```

默认会生成一份带时间戳的归档包，并维护 `latest` 指针：

```bash
build/server_app_bundle/docgen-server-app-YYYYMMDD-HHMMSS.tgz
build/server_app_bundle/docgen-server-app-YYYYMMDD-HHMMSS.tgz.sha256
build/server_app_bundle/docgen-server-app-YYYYMMDD-HHMMSS.manifest.json
build/server_app_bundle/docgen-server-app.tgz
build/server_app_bundle/docgen-server-app.tgz.sha256
build/server_app_bundle/docgen-server-app.manifest.json
build/server_app_bundle/latest-release.txt
build/server_app_bundle/latest-change-summary.txt
build/server_app_bundle/latest-release-notes.txt
build/server_app_bundle/latest-release-ops.txt
build/server_app_bundle/releases-index.txt
```

其中：

- `docgen-server-app-YYYYMMDD-HHMMSS.tgz` 是版本归档
- `docgen-server-app.tgz` 是指向最新归档的符号链接
- `docgen-server-app-YYYYMMDD-HHMMSS.manifest.json` 记录归档元数据与 SHA256
- `latest-release.txt` 记录当前最新归档文件名
- `latest-change-summary.txt` 提供人类可读的当前最新发布摘要
- `latest-change-summary.txt` 中的 `runtime_probes` 会显式列出稳定包装入口：
  - `scripts/verify_public_edge_health_stable.sh`
  - `scripts/report_docgen_runtime_health_stable.sh`
  - `scripts/verify_upload_parse_chain.sh`
  - `scripts/verify_generate_export_chain.sh`
- `latest-change-summary.txt` 中的 `operator_probes` 会显式列出只能在本机/运维侧执行的入口：
  - `scripts/verify_ui_upload_outline_chain.sh`
  - `scripts/verify_remote_ui_upload_outline_chain.sh`
  - `scripts/verify_remote_full_chain.sh`
- `latest-change-summary.txt` 中的 `operator_release_tools` 会显式列出只能在本机/运维侧执行的正式发版入口：
  - `scripts/package_docgen_server_app.sh`
  - `scripts/push_docgen_server_release.sh`
  - `scripts/push_docgen_server_worktree_scripts.sh`
  - `scripts/verify_remote_docgen_server_release_dir.sh`
  - `scripts/verify_remote_docgen_server_status.sh`
  - `scripts/verify_remote_docgen_server_readonly_inspection.sh`
  - `scripts/verify_remote_docgen_server_readonly_retention.sh`
- `latest-change-summary.txt` 中的 `server_release_tools` 会显式列出适合在服务器本机执行的 release 自检入口：
  - `scripts/verify_docgen_server_release_dir.sh`
  - `scripts/verify_docgen_server_worktree_scripts.sh`
  - `scripts/show_docgen_server_status.sh`
  - `scripts/report_docgen_server_readonly_inspection.sh`
  - `scripts/report_docgen_server_readonly_retention.sh`
  - `scripts/prune_docgen_server_readonly_inspection_logs.sh`
- `latest-change-summary.txt` 中的 `release_tools` 仍保留为上述两类工具的聚合字段，便于兼容旧校验逻辑：
  - `scripts/package_docgen_server_app.sh`
  - `scripts/push_docgen_server_release.sh`
  - `scripts/push_docgen_server_worktree_scripts.sh`
  - `scripts/verify_docgen_server_release_dir.sh`
  - `scripts/verify_docgen_server_worktree_scripts.sh`
  - `scripts/verify_remote_docgen_server_release_dir.sh`
  - `scripts/verify_remote_docgen_server_status.sh`
  - `scripts/show_docgen_server_status.sh`
  - `scripts/verify_remote_docgen_server_readonly_inspection.sh`
  - `scripts/verify_remote_docgen_server_readonly_retention.sh`
  - `scripts/report_docgen_server_readonly_inspection.sh`
  - `scripts/report_docgen_server_readonly_retention.sh`
  - `scripts/prune_docgen_server_readonly_inspection_logs.sh`
- `latest-release-notes.txt` 提供相对上一版的变化说明，包括归档条目新增、删除、同路径内容变更，以及按 `scripts/tests/docs/deploy/backend/root/other` 分类的摘要和分组高亮路径
- `latest-release-notes.txt` 还会给出 `impact_scope`，用于快速判断该版更偏：
  - `bootstrap`
  - `app-runtime`
  - `deploy-assets`
  - `tooling-only`
  - `metadata-only`
- `latest-release-notes.txt` 还会给出：
  - `operator_action`
  - `service_restart_recommended=yes/no`
  方便运维快速判断这版更像是“仅同步脚本”还是“需要走运行链发布”
- `latest-release-notes.txt` 还会给出：
  - `operator_release_tools_added`
  - `operator_release_tools_removed`
  - `server_release_tools_added`
  - `server_release_tools_removed`
  - `release_tools_added`
  - `release_tools_removed`
  便于判断“本机侧/服务器侧正式发版入口”是否发生变化
- `latest-release-ops.txt` 会直接给出这版 release 的推荐同步与校验命令，便于在拿到服务器凭据后直接执行
- 如果你要先只验证本地 `build/server_app_bundle/` 的 latest 指针、manifest/summary/notes/ops 和 checksum 是否一致，可直接运行：

```bash
bash ./scripts/verify_docgen_server_release_dir.sh build/server_app_bundle
```

如果你已经拿到服务器 SSH 凭据，并且要直接对远端 `/opt/docgen/releases` 做同样的 latest 一致性校验，可运行：

```bash
bash ./scripts/verify_remote_docgen_server_release_dir.sh root@199.180.118.204
```
- 如果你要把 latest manifest 声明的“服务器本机可执行脚本集合”同步到 `/opt/docgen/scripts`，可运行：

```bash
DOCGEN_PREVIEW=1 bash ./scripts/push_docgen_server_worktree_scripts.sh root@199.180.118.204
bash ./scripts/push_docgen_server_worktree_scripts.sh root@199.180.118.204
```

- 这条脚本会根据 latest manifest 中的：
  - `runtime_probes`
  - `server_release_tools`
  自动同步脚本到服务器工作树，并在远端执行一次：

```bash
bash /opt/docgen/scripts/verify_docgen_server_worktree_scripts.sh /opt/docgen /opt/docgen/releases
```

- 如果你只想单独从本机触发这条服务器工作树脚本自检，可直接运行：

```bash
ssh root@199.180.118.204 'bash /opt/docgen/scripts/verify_docgen_server_worktree_scripts.sh /opt/docgen /opt/docgen/releases'
```

- 如果你要把“release 目录一致性 + server worktree 脚本一致性 + runtime health”收口成一条服务器本机只读巡检，并把原始输出落到固定日志目录，可直接运行：

```bash
ssh root@199.180.118.204 'bash /opt/docgen/scripts/report_docgen_server_readonly_inspection.sh /opt/docgen https://doc.niyoufei.com'
```

- 这条脚本默认会把每次巡检日志落到：

```bash
/opt/docgen/logs/readonly_inspection/<timestamp>/
```

- 其中会生成：
  - `release-dir.log`
  - `server-worktree.log`
  - `runtime-health.log`
  - `readonly-retention.log`
  - `summary.txt`

- 每次执行后还会自动维护：

```bash
/opt/docgen/logs/readonly_inspection/latest -> <timestamp>/
/opt/docgen/logs/readonly_inspection/latest-run.txt
/opt/docgen/logs/readonly_inspection/latest-status.txt
```

- `latest-status.txt` 现在会把 retention preview 的最近状态一并收口进去，至少包括：
  - `readonly_retention_state`
  - `readonly_retention_run_id`
  - `readonly_retention_prune_candidates_count`
  - `readonly_retention_execute_allowed`

- 也就是说，执行一次 `report_docgen_server_readonly_inspection.sh` 或 `verify_remote_docgen_server_readonly_inspection.sh` 后：
  - inspection 自身会刷新
  - retention preview 状态也会一并刷新
  - 运维可优先读取 `/opt/docgen/logs/readonly_inspection/latest-status.txt` 作为统一状态面

- 如果你只想快速读取最近一次只读巡检结论，而不进入具体时间戳目录，可直接运行：

```bash
ssh root@199.180.118.204 'cat /opt/docgen/logs/readonly_inspection/latest-status.txt'
```

- 如果你只想读“当前服务器状态”，而不额外生成新的 inspection / retention 日志，可直接运行：

```bash
ssh root@199.180.118.204 'bash /opt/docgen/scripts/show_docgen_server_status.sh /opt/docgen'
```

- 这条状态脚本不会写日志，默认会汇总：
  - latest release 指针
  - inspection 统一状态
  - retention latest 状态与 inspection 中 retention 字段是否同步
  - `docgen-autoplan.service` 当前状态
  - backend / streamlit localhost health 当前状态

- 如果你更希望从本机单命令读取这条当前状态，可运行：

```bash
DOCGEN_PREVIEW=1 bash ./scripts/verify_remote_docgen_server_status.sh root@199.180.118.204
bash ./scripts/verify_remote_docgen_server_status.sh root@199.180.118.204
```

- 如果你要先预览“只读巡检日志保留策略”会删哪些旧目录，而不真正删除，可直接运行：

```bash
ssh root@199.180.118.204 'DOCGEN_READONLY_INSPECTION_KEEP_RUNS=10 bash /opt/docgen/scripts/prune_docgen_server_readonly_inspection_logs.sh /opt/docgen/logs/readonly_inspection'
```

- 只有在明确允许清理历史巡检日志时，才执行真实删除：

```bash
ssh root@199.180.118.204 'DOCGEN_READONLY_INSPECTION_KEEP_RUNS=10 DOCGEN_PRUNE_CONFIRM_RUN_ID=<retention_run_id> DOCGEN_PRUNE_CONFIRM_CANDIDATES=<candidate_csv> DOCGEN_PRUNE_EXECUTE=1 bash /opt/docgen/scripts/prune_docgen_server_readonly_inspection_logs.sh /opt/docgen/logs/readonly_inspection'
```

- 默认建议：
  - 先 preview
  - 再运行 `verify_remote_docgen_server_readonly_retention.sh` 或读取 `/opt/docgen/logs/readonly_retention/latest-status.txt`
  - 取出最新 `run_id` 与 `prune_candidates`
  - 再决定是否执行真实删除
  - 如果 `prune_candidates=none`，execute 会被脚本拒绝，不会当作 no-op 放行

- 如果你更希望从本机单命令触发这条远端只读巡检，可运行：

```bash
DOCGEN_PREVIEW=1 bash ./scripts/verify_remote_docgen_server_readonly_inspection.sh root@199.180.118.204
bash ./scripts/verify_remote_docgen_server_readonly_inspection.sh root@199.180.118.204
```

- 这条 wrapper 现在除了刷新 inspection 状态外，也会在远端顺带刷新一次 retention preview 状态。

- 如果你更希望从本机单命令触发“readonly inspection retention preview 状态更新”，可运行：

```bash
DOCGEN_PREVIEW=1 bash ./scripts/verify_remote_docgen_server_readonly_retention.sh root@199.180.118.204
bash ./scripts/verify_remote_docgen_server_readonly_retention.sh root@199.180.118.204
```

- 这条 wrapper 只会在服务器上生成 retention preview 状态面，不会执行真实删除。默认会维护：

```bash
/opt/docgen/logs/readonly_retention/latest -> <timestamp>/
/opt/docgen/logs/readonly_retention/latest-run.txt
/opt/docgen/logs/readonly_retention/latest-status.txt
```

- 如果你只想直接读取最近一次 retention 评估结论，可运行：

```bash
ssh root@199.180.118.204 'cat /opt/docgen/logs/readonly_retention/latest-status.txt'
```
- `releases-index.txt` 列出当前目录下可用归档版本
- `push_docgen_server_release.sh` 只负责同步 `build/server_app_bundle/` 到服务器 release 目录，并更新 latest 软链接，不会重启服务
- 它会一并同步：
  - 版本归档的 `summary/notes/ops`
  - latest 的 `latest-release.txt`
  - `latest-change-summary.txt`
  - `latest-release-notes.txt`
  - `latest-release-ops.txt`

这份部署包默认会包含：

- `rules_sample.json`
- `deploy/nginx/`
- `deploy/systemd/`
- `03_系统核心规则与字典/`
- `知识图谱/`

并排除本地运行垃圾目录。

如果你还不确定源站到底该走 `nginx` 还是 `caddy`，先在服务器上运行：

```bash
bash ./detect_linux_proxy_stack.sh doc.niyoufei.com
```

这个脚本会输出：
- `nginx/caddy` 命令是否存在
- `nginx/caddy` service 是否 `active`
- `127.0.0.1:80/443` 的响应码和 `server` 头
- `Caddyfile` 是否导入 `conf.d`
- 目标域名的 Let's Encrypt 证书是否存在
- 推荐的 `proxy_stack`

探测后如果还不确定下一步应该先补证书还是先装反代，可继续运行：

```bash
bash ./suggest_linux_origin_fix.sh doc.niyoufei.com
```

它会根据：
- 探测到的 `proxy_stack`
- `Let's Encrypt` 证书是否存在并覆盖域名
- `Caddyfile` 是否已导入 `conf.d`

直接输出下一步建议命令。

排查 Cloudflare 到源站的连通性时，可以直接运行：

```bash
./scripts/diagnose_domain_route.sh doc.niyoufei.com 199.180.118.204
```

这个脚本会同时输出：
- 域名边缘 HTTP 状态
- 域名边缘 HTTPS 状态
- 带 `Host/SNI` 的源站 80/443 直连结果
- 对 `521`、`525`、空响应的简要判读
- 对 `198.18.0.0/15` fake-IP 的提醒

4. 公开地址

在服务环境变量中设置：

```bash
ZF_PUBLIC_WEB_URL=https://doc.niyoufei.com
```

这样桌面启动器、启动脚本和提示信息会优先打开公网域名，而不是 `127.0.0.1:8501`。

注意：
- 当前模板默认走 Cloudflare 代理到源站 80 端口，再由 Nginx 转发到 `127.0.0.1:8501`。
- 若 Cloudflare SSL 模式不是 `Flexible`，需要同时在源站配置 443 与证书；否则 Cloudflare 会返回 `525`。
- 单域名证书例如 `CN=niyoufei.com` 并不会自动覆盖 `doc.niyoufei.com`；子域名通常需要单独证书或通配符证书。

如果你还没有 `doc.niyoufei.com` 的证书，但已经拿到了服务器登录权限，可以先在服务器上生成 CSR：

```bash
bash ./scripts/generate_origin_tls_csr.sh doc.niyoufei.com
```

默认输出：

```bash
build/tls_csr/doc.niyoufei.com/
```

其中包含：
- 私钥：`doc.niyoufei.com.key`
- CSR：`doc.niyoufei.com.csr`
- OpenSSL 配置：`doc.niyoufei.com.openssl.cnf`

生成 CSR 后，你可以：
- 交给 Let's Encrypt / 现有 CA 签发
- 或在 Cloudflare Origin CA 中使用 CSR 签发源站证书

证书签发完成后，再设置：

```bash
export DOCGEN_SSL_CERT=/path/to/fullchain.pem
export DOCGEN_SSL_KEY=/path/to/privkey.pem
```

然后重新打包或安装域名 bundle。

如果你准备沿用服务器上常见的 Let's Encrypt 目录结构，也可以不手工填路径，直接使用：

```bash
export DOCGEN_SSL_PROFILE=letsencrypt
```

此时脚本会自动采用：

```bash
/etc/letsencrypt/live/doc.niyoufei.com/fullchain.pem
/etc/letsencrypt/live/doc.niyoufei.com/privkey.pem
```

## 可选：Caddy 反代栈

如果源站已经统一使用 `Caddy` 管理 `80/443`，不要再在同一台机器上盲目叠加一套新的 `Nginx` 监听。

可参考模板：

- [Caddyfile.docgen-streamlit.template](/Users/youfeini/Desktop/文档生成系统/deploy/caddy/Caddyfile.docgen-streamlit.template)

这个模板会把：

- `https://__DOCGEN_DOMAIN__`
- 反代到 `127.0.0.1:8501`

适用前提：

- 服务器上已经在用 `caddy` 作为主反向代理
- 你能安全修改现有 `/etc/caddy/Caddyfile` 或其导入链
- Cloudflare `SSL/TLS` 建议使用 `Full (strict)`

如果你走 Caddy 路线，源站自检时可改用：

```bash
DOCGEN_PROXY_STACK=caddy \
CADDY_CONFIG_PATH=/etc/caddy/Caddyfile \
bash ./verify_linux_domain_origin.sh doc.niyoufei.com
```

当前打包/上传脚本也支持 `DOCGEN_PROXY_STACK=caddy`：

```bash
DOCGEN_PROXY_STACK=caddy \
bash ./scripts/package_linux_domain_bundle.sh doc.niyoufei.com
```

或：

```bash
DOCGEN_PROXY_STACK=caddy \
bash ./scripts/push_linux_domain_bundle.sh doc.niyoufei.com root@199.180.118.204
```

注意：
- bundle 会同时生成 `Nginx` 和 `Caddy` 配置
- 安装时实际采用哪一套，由 `DOCGEN_PROXY_STACK` 决定
- Caddy 路线默认会把片段复制到 `/etc/caddy/conf.d/`
- 只有当主 `Caddyfile` 已经 `import` 该目录或目标片段时，安装脚本才会继续执行
