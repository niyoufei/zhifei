# AGENTS.md

## 1. 适用范围
本文件适用于 `clawdbot/` 目录及其默认继承的子目录。
如更下层存在新的 `AGENTS.md`，以更近层级规则为准。

---

## 2. 目录角色定义
`clawdbot/` 当前按以下角色理解：

- 独立代理脚本链
- 外部 CLI 驱动链
- 循环执行脚本链
- 提示词文件与状态文件管理目录
- 非 FastAPI 主服务目录

本目录当前不是已确认的在线主链组成部分。

---

## 3. 与当前在线主链的关系
当前已确认的在线链分为两部分：

V2 页面主链：

`app.py -> backend/app/main.py -> backend/app/routers/actions_bridge.py -> backend/zhifei_autoplan/*`

兼容 API 链：

`backend/app/main.py -> backend/app/routers/zhifei_autoplan.py -> backend/zhifei_autoplan/*`

截至当前体检，可确认：
- `clawdbot/run.sh` 存在
- `clawdbot/supervisor_prompt.txt` 存在
- 当前未确认 `clawdbot/` 接入 FastAPI 主入口
- 当前未确认 `clawdbot/` 属于主服务必经链路

因此，本目录默认标注为：
- 独立脚本链
- 旁路能力链
- 实验/辅助执行链

不得直接写成当前在线主链事实。

---

## 4. 本目录检查目标
后续检查本目录时，只做以下几类判断：

### 4.1 判断执行方式
确认其是否依赖：
- 外部 CLI
- shell 循环调度
- prompt 文件驱动
- 状态文件驱动
- stop/done 标记文件

### 4.2 判断与主链是否存在真实接线
必须先确认：
- 是否被 `devserver.py` 调用
- 是否被 `backend/app/main.py` 调用
- 是否被 `backend/app/routers/*` 调用
- 是否只是独立 shell 脚本自运行

### 4.3 判断是否需要长期保留
若本目录仅用于试验、演示、代理自动跑批，应单独标识为：
- 实验目录
- 独立工具目录
- 可归档目录

---

## 5. 修订原则
### 5.1 先隔离，再评估
本目录的处理优先做：
- 边界说明
- 依赖说明
- 状态文件说明
- 是否仍在使用的判断

### 5.2 不跨链修改主服务
未确认真实接入关系前，不得为了整理 `clawdbot/`，直接改动：
- `devserver.py`
- `backend/app/main.py`
- `backend/app/routers/zhifei_autoplan.py`

### 5.3 若未来要接入主链，必须单独补方案
如后续准备让 `clawdbot/` 接入主链，必须单独补齐：
- 接入方式
- 调用入口
- 失败回退
- 审计留痕
- 与主服务冲突规避

---

## 6. 禁止事项
### 6.1 禁止误判为主链
禁止把 `clawdbot/` 直接写成：
- 当前 V2 页面主链
- 当前 FastAPI 子服务
- 当前主服务必经流程

### 6.2 禁止跳过引用分析直接重构
未确认主链真实引用前，不得以“功能看起来有用”为由直接并入主服务。

### 6.3 禁止把脚本状态当生产事实
本目录中的：
- status 文件
- blockers 文件
- stop/done 标记
- prompt 文件
默认视为脚本运行态，不得直接当成主服务生产状态。

---

## 7. 当前事实基线
截至当前体检，可确认：

- `clawdbot/` 目录存在
- `run.sh` 存在
- `supervisor_prompt.txt` 存在
- 当前未确认接入 FastAPI 主入口
- 当前应视为独立脚本链 / 旁路链

---

## 8. 默认处理策略
进入本目录后，默认按以下顺序处理：

1. 识别脚本职责
2. 核对是否被主链真实调用
3. 判断是否仅为独立运行工具
4. 决定是否保留或归档
5. 最后再考虑整理、重构、迁移
