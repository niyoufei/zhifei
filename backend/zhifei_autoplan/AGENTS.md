# AGENTS.md

## 1. 适用范围
本文件适用于 `backend/zhifei_autoplan/` 目录及其默认继承的子目录。
如更下层存在新的 `AGENTS.md`，以更近层级规则为准。

---

## 2. 目录角色定义
`backend/zhifei_autoplan/` 当前按以下角色理解：

- AutoPlan 主业务实现层
- 当前在线主链核心业务目录
- 编排、导出、知识图谱、任务状态、格式化、优化等实现层
- 被 `backend/app/routers/zhifei_autoplan.py` 调用的下游业务模块目录

本目录属于当前已确认的在线主链组成部分。

---

## 3. 与当前在线主链的关系
当前已确认的在线链分为两部分：

V2 页面主链：

`app.py -> backend/app/main.py -> backend/app/routers/actions_bridge.py -> backend/zhifei_autoplan/*`

兼容 API 链：

`backend/app/main.py -> backend/app/routers/zhifei_autoplan.py -> backend/zhifei_autoplan/*`

目录分层关系如下：
- `app.py`：V2 页面入口
- `devserver.py`：历史兼容启动壳
- `backend/app/main.py`：FastAPI 主入口
- `backend/app/routers/`：接口入口层
- `backend/zhifei_autoplan/`：业务实现层
- `backend/data/`：配置、审计、KG、状态等落盘层

因此，本目录默认视为：
- 当前主链核心实现目录
- 主服务变更高敏感目录
- 需要重点审阅与备份的目录

---

## 4. 本目录检查目标
后续检查本目录时，优先做以下判断：

### 4.1 判断模块职责
确认文件属于哪一类：
- 编排层
- 导出层
- 知识图谱运行层
- 任务/计划存储层
- 解析层
- 优化层
- 样式/格式构建层
- 用户/计费/审计关联逻辑

### 4.2 判断与入口层的调用关系
重点核对：
- 是否被 `backend/app/routers/actions_bridge.py` 直接引用
- 是否被 `backend/app/routers/zhifei_autoplan.py` 直接引用
- 是否被 `orchestrator.py` 主编排链实际调用
- 是否属于主链必经模块
- 是否只是旁路/实验模块

### 4.3 判断与状态落盘层的关系
重点核对：
- `backend/data/autoplan/`
- `backend/data/audit/`
- `backend/data/kg/`
- `build/`

必须明确：
- 谁负责写
- 谁负责读
- 谁负责导出
- 谁负责审计留痕

### 4.4 判断实验链与主链边界
对以下对象必须特别区分：
- `v2/`
- `graph_dispatcher`
- 外部知识图谱目录
- 多 agent / self-healing 类逻辑

未确认接入关系前，不得直接写成主链事实。

---

## 5. 修订原则
### 5.1 本目录改动属于主链核心改动
凡修改本目录内文件，均按主链核心业务改动处理。

### 5.2 先备份，再修改
涉及以下内容的修改，必须先备份原文件：
- 编排主链
- 导出逻辑
- KG 运行逻辑
- 任务状态逻辑
- 审计/计费相关逻辑

### 5.3 一次只改一类问题
不得同时混改：
- 编排链
- KG 链
- 导出链
- 审计链
- 计划/任务链
- v2 实验链

### 5.4 改后必须复检
每次改动后，至少复检：
- `backend/app/routers/zhifei_autoplan.py` 是否仍可正常导入
- `_autodoctor/summary.md` 主链结论是否稳定
- `backend/data/audit/` 是否仍有审计源
- `build/` 是否仍能正常落盘
- `backend/data/kg/` 状态文件是否正常

---

## 6. 与其他目录的边界
### 6.1 与 `backend/app/routers/` 的边界
- `backend/app/routers/`：接口入口层
- `backend/zhifei_autoplan/`：业务实现层

### 6.2 与 `backend/data/` 的边界
- `backend/zhifei_autoplan/`：业务处理与读写动作发起层
- `backend/data/`：状态、配置、审计、KG 等落盘层

### 6.3 与 `v2/` 的边界
- `backend/zhifei_autoplan/` 主体目录：当前在线主链实现层
- `backend/zhifei_autoplan/v2/`：当前视为实验/旁路链

不得混淆。

---

## 7. 禁止事项
### 7.1 禁止把实验链自动并入主链结论
即使 `v2/`、`graph_dispatcher`、multi-agent 逻辑存在，也不得自动视为当前主链必经实现。

### 7.2 禁止跨层只修表面
若问题属于接口入口层，不应只在本目录盲修。
若问题属于落盘状态层，也不应只在本目录表面绕过。

### 7.3 禁止未核对调用关系就删改核心模块
未确认真实引用关系前，不得删除、重命名或大幅重构：
- `orchestrator.py`
- `exporter.py`
- `kg_store.py`
- `kg_runtime.py`
- 任务/计划存储相关模块

---

## 8. 当前事实基线
截至当前体检，可确认：

- `backend/zhifei_autoplan/` 属于当前在线主链核心实现目录
- 当前 V2 页面主链通过 `actions_bridge.py` 进入本目录
- `/autoplan/*` 兼容链也会进入本目录
- `orchestrator.py` 位于主编排链
- `exporter.py` 属于导出引擎
- `kg_store.py`、`kg_runtime.py` 属于当前在线 KG 运行链
- `backend/data/kg/` 为当前在线 KG 状态目录
- `v2/` 当前未确认接入主入口在线链

---

## 9. 默认处理策略
进入本目录后，默认按以下顺序处理：

1. 先识别模块职责
2. 再确认是否被主链真实调用
3. 再确认其对应的落盘目录
4. 再判断是否属于主链修复范围
5. 最后再做修改、重构、清理
