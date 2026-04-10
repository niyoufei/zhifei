# 当前在线主链与遗留入口清单

本文档只回答一个问题：当前正在服务 `施组专家系统 V2.0` 的真实在线链路是什么，哪些入口只是兼容层、离线路径或遗留工具。

## 1. 当前在线主链

当前页面入口：

- Streamlit 页面：[app.py](/Users/youfeini/Desktop/文档生成系统/app.py)
- 默认页面地址：`http://127.0.0.1:8501`

当前后端入口：

- FastAPI 主入口：[backend/app/main.py](/Users/youfeini/Desktop/文档生成系统/backend/app/main.py)
- 默认后端地址：`http://127.0.0.1:8010`

当前 V2 页面实际主链：

`app.py (Streamlit)` -> `backend/app/main.py` -> `/actions/*` -> `backend/app/routers/actions_bridge.py` -> `backend/zhifei_autoplan/*`

前端在页面内直接调用的关键接口：

- `/actions/tender/parse`
- `/actions/boq/parse`
- `/actions/plan/save`
- `/actions/generate_async`
- `/actions/job_status`
- `/actions/download`

## 2. 兼容层

以下路由仍在线，但不是当前 V2 页面主走向：

- [backend/app/routers/zhifei_autoplan.py](/Users/youfeini/Desktop/文档生成系统/backend/app/routers/zhifei_autoplan.py)

说明：

- 该路由前缀为 `/autoplan`
- 仍承载历史接口、批量导出、审计查询等能力
- 适合作为兼容层或脚本调用入口
- 不应再被表述为“当前 V2 Web 页面主链”

## 3. 未接线 / 离线工具

以下文件当前不在 `backend/app/main.py` 主入口挂载链路中：

- [routers/assist_codex.py](/Users/youfeini/Desktop/文档生成系统/routers/assist_codex.py)
- [backend/routers/assist_codex.py](/Users/youfeini/Desktop/文档生成系统/backend/routers/assist_codex.py)

以下文件属于离线脚本或本地运维工具，不属于在线请求链：

- [check_audit.py](/Users/youfeini/Desktop/文档生成系统/check_audit.py)
- [replay_audit.py](/Users/youfeini/Desktop/文档生成系统/replay_audit.py)
- [clawdbot/supervisor_prompt.txt](/Users/youfeini/Desktop/文档生成系统/clawdbot/supervisor_prompt.txt)
- [devserver.py](/Users/youfeini/Desktop/文档生成系统/devserver.py)

## 4. 排障时的推荐顺序

如果问题出在页面生成主流程，请按下面顺序排查：

1. [app.py](/Users/youfeini/Desktop/文档生成系统/app.py)
2. [backend/app/main.py](/Users/youfeini/Desktop/文档生成系统/backend/app/main.py)
3. [backend/app/routers/actions_bridge.py](/Users/youfeini/Desktop/文档生成系统/backend/app/routers/actions_bridge.py)
4. [backend/zhifei_autoplan/orchestrator.py](/Users/youfeini/Desktop/文档生成系统/backend/zhifei_autoplan/orchestrator.py)
5. [backend/zhifei_autoplan/exporter.py](/Users/youfeini/Desktop/文档生成系统/backend/zhifei_autoplan/exporter.py)
6. [backend/zhifei_autoplan/job_worker.py](/Users/youfeini/Desktop/文档生成系统/backend/zhifei_autoplan/job_worker.py)

## 5. 当前结论

一句话总结：

- `actions_bridge.py` 是当前 V2 页面在线主链
- `zhifei_autoplan.py` 是在线兼容层
- `assist_codex.py`、`check_audit.py`、`replay_audit.py`、`clawdbot/`、`devserver.py` 不是当前页面生成主链

## 6. 建议退役 / 弱化顺序

建议优先级从高到低如下：

1. 文档层先统一口径，今后不再把 `/autoplan` 表述为 V2 页面主链。
2. [devserver.py](/Users/youfeini/Desktop/文档生成系统/devserver.py) 保留兼容即可，不再作为任何启动文档的首选入口。
3. [routers/assist_codex.py](/Users/youfeini/Desktop/文档生成系统/routers/assist_codex.py) 与 [backend/routers/assist_codex.py](/Users/youfeini/Desktop/文档生成系统/backend/routers/assist_codex.py) 若后续三轮迭代仍未接线，可考虑移入 `legacy/` 或直接删除。
4. [replay_audit.py](/Users/youfeini/Desktop/文档生成系统/replay_audit.py) 当前使用的日志路径与现网不一致，若无历史依赖，优先退役或重写到现网审计格式。
5. [check_audit.py](/Users/youfeini/Desktop/文档生成系统/check_audit.py) 可保留为运维小工具，但应明确只用于离线本地核验。
