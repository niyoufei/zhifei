# AGENTS.md

## 1. 适用范围
本文件适用于 `backend/app/routers/` 目录及其默认继承的子目录。
如更下层存在新的 `AGENTS.md`，以更近层级规则为准。

---

## 2. 目录角色定义
`backend/app/routers/` 当前按以下角色理解：

- FastAPI 主服务正式路由目录
- 当前在线接口挂载目录
- 主链业务入口层
- 与 `backend/app/main.py` 直接关联的路由层

本目录属于当前已确认的在线主链组成部分。

---

## 3. 与当前在线主链的关系
当前已确认的在线链分为两部分：

V2 页面主链：

`app.py -> backend/app/main.py -> backend/app/routers/actions_bridge.py -> backend/zhifei_autoplan/*`

兼容 API 链：

`backend/app/main.py -> backend/app/routers/zhifei_autoplan.py -> backend/zhifei_autoplan/*`

其中：
- `devserver.py` 为启动壳
- `backend/app/main.py` 为 FastAPI 主入口
- `backend/app/routers/` 为正式路由挂载目录

截至当前体检，可确认 `backend/app/main.py` 挂载的主路由包括：
- `ingest_router`
- `retrieve_router`
- `publish_router`
- `score_router`
- `zhifei_autoplan_router`
- `actions_bridge_router`
- `auth_router`

其中：
- `actions_bridge.py`：当前 V2 页面主走路由
- `zhifei_autoplan.py`：兼容 API / KG / 审计能力路由

因此，本目录默认视为：
- 当前在线主链正式路由层
- 优先检查目录
- 主服务变更敏感目录

---

## 4. 本目录检查目标
后续检查本目录时，优先做以下判断：

### 4.1 判断路由是否真实挂载
确认每个路由模块是否被 `backend/app/main.py` 真实 `include_router`。

### 4.2 判断接口职责边界
确认接口属于哪一类：
- 文档解析
- 检索
- 发布
- 评分
- AutoPlan 主业务
- Actions Bridge
- 鉴权

### 4.3 判断与下游业务模块的连接关系
重点核对：
- `backend/zhifei_autoplan/*`
- 导出链
- 审计链
- KG 在线链
- 用户/鉴权链

### 4.4 判断是否存在重复路由或历史残留
若发现同名、近似名、备份型路由文件，应优先标注，不直接删除。

---

## 5. 修订原则
### 5.1 本目录改动属于主链改动
凡修改本目录内文件，均按主链变更处理。

### 5.2 先备份，再修改
涉及路由前缀、请求体、响应体、导入关系、挂载关系的改动，先备份原文件。

### 5.3 一次只改一类问题
不得同时混改：
- 路由挂载
- 业务编排
- 审计逻辑
- 导出逻辑
- KG 逻辑
- 鉴权逻辑

### 5.4 改后必须复检
每次改动后，至少复检：
- `backend/app/main.py` 挂载关系
- 目标路由文件语法
- 主链体检报告
- 审计源与导出目录是否仍正常

---

## 6. 与其他目录的边界
### 6.1 与根目录 `routers/` 的边界
- `backend/app/routers/`：正式在线主链路由目录
- `routers/`：当前视为旁路/试验路由目录

不得混淆。

### 6.2 与 `backend/zhifei_autoplan/` 的边界
- `backend/app/routers/`：接口入口层
- `backend/zhifei_autoplan/`：业务实现层

### 6.3 与 `backend/data/` 的边界
- `backend/app/routers/`：发起读写动作
- `backend/data/`：状态、配置、审计、KG 等落盘目录

---

## 7. 禁止事项
### 7.1 禁止把旁路路由误并入本目录结论
不得因为其他目录中存在 FastAPI 风格代码，就把其自动视为正式挂载路由。

### 7.2 禁止未核对挂载关系就删改路由
未确认 `backend/app/main.py` 的引用前，不得删除或重命名本目录中的路由文件。

### 7.3 禁止跨层直接改业务实现
若问题属于 `backend/zhifei_autoplan/*` 实现层，不应只在本目录做表面修补。

---

## 8. 当前事实基线
截至当前体检，可确认：

- `backend/app/routers/` 属于当前在线主链正式路由目录
- `actions_bridge.py` 是当前 V2 页面在线主业务路由
- `zhifei_autoplan.py` 保持在线，但主要承担兼容 API、KG、审计等能力
- `/kg/*` 在线知识图谱接口位于本目录下的 `zhifei_autoplan.py`
- 审计导出相关接口也位于 `zhifei_autoplan.py`
- 根目录 `routers/` 当前不作为正式路由目录判定依据

---

## 9. 默认处理策略
进入本目录后，默认按以下顺序处理：

1. 先确认挂载关系
2. 再确认接口职责
3. 再确认下游实现模块
4. 再判断是否属于主链修复范围
5. 最后再做修改、重构、清理
