# 公网首页切换 Runbook

## 目标

将正式域名 `https://doc.niyoufei.com` 的公网首页，从当前的 Open WebUI 登录页，切换为本项目的“文档生成系统”页面。

本 Runbook 只覆盖最小切换路径：

- 保持 Cloudflare / 证书 / xray / 443 结构不变
- 保持源站域名不变
- 仅把 `doc.niyoufei.com` 当前站点的上游，从旧 Open WebUI 入口切到 `127.0.0.1:8501`

## 当前前提

- 本地文档生成系统页面主入口是 `app.py`
- 本地页面默认监听 `127.0.0.1:8501`
- 源站 Nginx 模板已经具备反代到 `127.0.0.1:8501` 的能力：
  - [docgen-streamlit-origin.conf.template](/Users/youfeini/Desktop/文档生成系统/deploy/nginx/docgen-streamlit-origin.conf.template)
  - [docgen-streamlit-origin-ssl.conf.template](/Users/youfeini/Desktop/文档生成系统/deploy/nginx/docgen-streamlit-origin-ssl.conf.template)
- 当前公网 `doc.niyoufei.com` 仍是 Open WebUI 登录页，尚未执行切换

## 切换前门禁

如果希望先拿到一份总控状态报告，可先在本机执行：

```bash
bash /Users/youfeini/Desktop/文档生成系统/scripts/report_public_homepage_cutover_status.sh 60
```

如果只想看简短结论，不输出明细日志，可执行：

```bash
ZF_STATUS_SUMMARY_ONLY=1 bash /Users/youfeini/Desktop/文档生成系统/scripts/report_public_homepage_cutover_status.sh 60
```

它会同时输出：

- 本地 readiness 结果
- 本地文档生成首页验收
- 当前公网首页状态
- `push` 辅助链回归
- cutover 资产回归

并汇总结论：

- `ready_to_apply=yes/no`
- `public_homepage_state=open-webui/docgen/unknown`
- `public_cutover_needed=yes/no/unknown`
- `next_action=apply_public_cutover/fix_local_readiness/fix_local_homepage/fix_cutover_tooling/inspect_public_homepage/none_already_cutover`

如果要把“公网边缘可达性”和“源站应用健康”拆开看，建议在源站额外使用三支独立探针：

```bash
bash ./verify_public_edge_health.sh https://doc.niyoufei.com
```

```bash
bash ./verify_origin_app_health.sh
```

```bash
DOCGEN_RUNTIME_SUMMARY_ONLY=1 bash ./report_docgen_runtime_health.sh https://doc.niyoufei.com
```

如果希望把 Cloudflare 边缘抖动的误报再压低一层，可直接切到“多轮观察 + 连续失败阈值”模式：

```bash
bash ./verify_public_edge_health_stable.sh https://doc.niyoufei.com
```

```bash
bash ./report_docgen_runtime_health_stable.sh https://doc.niyoufei.com
```

如果需要显式看到稳定模式背后的 profile 配置，仍可直接使用底层脚本：

```bash
ZF_EDGE_PROFILE=stable bash ./verify_public_edge_health.sh https://doc.niyoufei.com
```

```bash
ZF_EDGE_PROFILE=stable DOCGEN_RUNTIME_SUMMARY_ONLY=1 bash ./report_docgen_runtime_health.sh https://doc.niyoufei.com
```

当前 `ZF_EDGE_PROFILE=stable` 等价于：

- `ZF_EDGE_OBSERVE_CYCLES=3`
- `ZF_EDGE_HOME_FAIL_STREAK_THRESHOLD=2`
- `ZF_EDGE_STREAMLIT_FAIL_STREAK_THRESHOLD=2`

如果需要，也可以继续用显式环境变量覆盖这些默认值。

它们分别负责：

- `verify_public_edge_health.sh`
  - 只验证公网入口和 `/_stcore/health` 是否能经由 Cloudflare 正常到达
- `verify_origin_app_health.sh`
  - 只验证源站本机 `8010` 与 `8501` 是否健康
- `report_docgen_runtime_health.sh`
  - 汇总 `origin_app_state`
  - 汇总 `public_edge_state`
  - 同时保留 `public_homepage_state=docgen/open-webui/unknown`

这样可以避免把边缘 TLS/网络抖动误判成源站应用异常。

阈值模式下，边缘探针会额外输出：

- `observe_cycles`
- `edge_profile`
- `edge_home_fail_streak_threshold`
- `edge_streamlit_fail_streak_threshold`
- `edge_home_drop_at`
- `edge_streamlit_drop_at`

先在本机执行：

```bash
bash /Users/youfeini/Desktop/文档生成系统/scripts/check_public_homepage_readiness.sh 180
```

需要满足：

- `backend_health=ok`
- `web_health=ok`
- `web_home=ok`
- `web_pid_aligned=yes`
- `observe_result=pass`
- `public_cutover_ready=yes`

如果希望把主链冒烟也纳入门禁，再执行：

```bash
ZF_INCLUDE_SMOKE=1 bash /Users/youfeini/Desktop/文档生成系统/scripts/check_public_homepage_readiness.sh 180
```

## 源站最小切换动作

先在源站只读定位当前 conf：

```bash
bash ./inspect_public_homepage_origin_conf.sh doc.niyoufei.com
```

如果只命中一个 conf，脚本会直接打印：

- `target_conf_path=...`
- `cutover_dry_run=...`
- `cutover_apply=...`

如果源站不是简单的单 nginx conf，而是类似：

- `xray:443 -> nginx:23890`
- 或 `xray fallback -> 31302 / 31300`

这类多 upstream 拓扑，先运行：

```bash
bash ./inspect_public_homepage_live_topology.sh doc.niyoufei.com
```

它会只读输出：

- 命中的 nginx conf
- 当前 `proxy_pass` 指向
- 命中的 xray fallback / target 线索
- 建议需要替换的 `3000 -> 8501` patch 数量
- 是否应保持 `xray / Cloudflare / DNS` 不动

如果输出 `patch_count>1`，优先使用：

```bash
bash ./cutover_public_homepage_upstream_targets.sh doc.niyoufei.com /etc/nginx/conf.d/doc.conf /etc/nginx/conf.d/alone.conf
```

真正写入：

```bash
DOCGEN_APPLY=1 bash ./cutover_public_homepage_upstream_targets.sh doc.niyoufei.com /etc/nginx/conf.d/doc.conf /etc/nginx/conf.d/alone.conf
```

这个脚本不会重渲染整份 conf，而是只把目标 conf 里命中的：

- `proxy_pass http://127.0.0.1:3000;`

改成：

- `proxy_pass http://127.0.0.1:8501;`

并在 `nginx -t` 失败时自动恢复备份。

如果希望直接串起“定位 -> dry-run -> apply -> verify”，可在源站使用：

```bash
bash ./execute_public_homepage_cutover.sh doc.niyoufei.com
```

真正执行切换：

```bash
DOCGEN_APPLY=1 DOCGEN_SSL_PROFILE=letsencrypt \
bash ./execute_public_homepage_cutover.sh doc.niyoufei.com
```

如果本机已经有 SSH 权限，也可以直接从本机发起：

```bash
DOCGEN_PREVIEW=1 \
bash /Users/youfeini/Desktop/文档生成系统/scripts/push_public_homepage_cutover.sh doc.niyoufei.com root@199.180.118.204
```

确认远程 `scp/ssh` 命令链无误后，再做源站 dry-run：

```bash
bash /Users/youfeini/Desktop/文档生成系统/scripts/push_public_homepage_cutover.sh doc.niyoufei.com root@199.180.118.204
```

如果只想在本机假跑一遍 `scp/ssh` 调用顺序，可用 mock 二进制覆盖：

```bash
DOCGEN_SCP_BIN=/tmp/mock-scp.sh \
DOCGEN_SSH_BIN=/tmp/mock-ssh.sh \
bash /Users/youfeini/Desktop/文档生成系统/scripts/push_public_homepage_cutover.sh doc.niyoufei.com root@199.180.118.204
```

如果希望在切换后优先直连源站验证，而不是先走公网链路，可附带：

```bash
DOCGEN_VERIFY_RESOLVE_IP=<源站IP> \
bash /Users/youfeini/Desktop/文档生成系统/scripts/push_public_homepage_cutover.sh doc.niyoufei.com root@199.180.118.204
```

真正执行切换：

```bash
DOCGEN_REMOTE_APPLY=1 DOCGEN_SSL_PROFILE=letsencrypt \
bash /Users/youfeini/Desktop/文档生成系统/scripts/push_public_homepage_cutover.sh doc.niyoufei.com root@199.180.118.204
```

如果 apply 后希望也先走源站直连验收：

```bash
DOCGEN_REMOTE_APPLY=1 DOCGEN_SSL_PROFILE=letsencrypt DOCGEN_VERIFY_RESOLVE_IP=<源站IP> \
bash /Users/youfeini/Desktop/文档生成系统/scripts/push_public_homepage_cutover.sh doc.niyoufei.com root@199.180.118.204
```

1. 备份当前 `doc.niyoufei.com` 线上站点配置
2. 保持现有 `server_name doc.niyoufei.com` 不变
3. 仅把 `location /` 的上游切到 `http://127.0.0.1:8501`
4. 保留以下反代头与超时设置：

来自 [docgen-streamlit-origin-ssl.conf.template](/Users/youfeini/Desktop/文档生成系统/deploy/nginx/docgen-streamlit-origin-ssl.conf.template)：

- `proxy_set_header Host $host;`
- `proxy_set_header Upgrade $http_upgrade;`
- `proxy_set_header Connection $connection_upgrade;`
- `proxy_set_header X-Real-IP $remote_addr;`
- `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`
- `proxy_set_header X-Forwarded-Proto $scheme;`
- `proxy_set_header X-Forwarded-Host $host;`
- `client_max_body_size 1024m;`
- `proxy_read_timeout 86400;`
- `proxy_send_timeout 86400;`

5. `nginx -t` 通过后再 reload

如果希望把“备份当前 conf + 渲染模板 + 写入 + `nginx -t` + reload”固化成一条命令，可在源站上使用：

```bash
DOCGEN_APPLY=1 DOCGEN_SSL_PROFILE=letsencrypt \
bash ./cutover_public_homepage_origin.sh doc.niyoufei.com /etc/nginx/conf.d/doc.niyoufei.com.conf
```

默认不写入的 dry-run 用法：

```bash
bash ./cutover_public_homepage_origin.sh doc.niyoufei.com /etc/nginx/conf.d/doc.niyoufei.com.conf
```

该脚本会：

- 先渲染当前域名的 Nginx 配置
- `DOCGEN_APPLY=1` 时自动备份原 conf
- 写入新 conf
- 运行 `nginx -t`
- 仅在语法通过后 reload

## 切换后验收

源站验收：

```bash
curl -fsS http://127.0.0.1:8501/_stcore/health
curl -kI --resolve doc.niyoufei.com:443:199.180.118.204 https://doc.niyoufei.com
```

本机入口稳定性验收：

```bash
bash /Users/youfeini/Desktop/文档生成系统/scripts/observe_web_stability.sh 180
```

主链冒烟：

```bash
cd /Users/youfeini/Desktop/文档生成系统
set -a
. ./.runtime/local_keys.env >/dev/null 2>&1
set +a
python3 -u backend/scripts/smoke_e2e.py
```

说明：
- 该命令默认走当前 `/actions` 主链 smoke
- `/compose` 兼容链不再作为页面发布门禁

公网验收：

```bash
curl -I https://doc.niyoufei.com
```

期望：

- `HTTP/2 200`
- 页面已不再是 Open WebUI 登录页
- 文档生成系统首页可正常打开

推荐直接执行统一验收脚本：

```bash
bash /Users/youfeini/Desktop/文档生成系统/scripts/verify_public_homepage_cutover.sh https://doc.niyoufei.com
```

如果需要先直连源站验证：

```bash
bash /Users/youfeini/Desktop/文档生成系统/scripts/verify_public_homepage_cutover.sh https://doc.niyoufei.com 199.180.118.204
```

脚本会同时检查：

- 首页 `HEAD /` 是否 `200`
- `/_stcore/health` 正文是否为 `ok`
- 首页正文是否仍包含 `Open WebUI`

## 回退

如果切换后发现页面异常：

1. 恢复原来的 `doc.niyoufei.com` 站点配置备份
2. `nginx -t`
3. `systemctl reload nginx`

回退后再次确认：

```bash
curl -I https://doc.niyoufei.com
```

## 备注

- 本 Runbook 是“最小切换方案”，不涉及 Cloudflare、证书、xray、443 结构调整
- 如果后续要把 Open WebUI 保留下来，建议改为新的独立子域，而不是继续占用 `doc.niyoufei.com`
