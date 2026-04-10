# AGENTS.md

## 1. 适用范围
本文件适用于 `backend/zhifei_autoplan/v2/` 目录及其默认继承的子目录。
如更下层存在新的 `AGENTS.md`，以更近层级规则为准。

---

## 2. 目录角色定义
`backend/zhifei_autoplan/v2/` 当前按以下角色理解：

- 图谱处理实验链
- 多阶段图谱 ingestion / pipeline 链
- graph dispatcher 相关能力链
- 自愈/补丁/实验性图谱处理链
- 非主入口默认链路

本目录当前不是已确认的 FastAPI 在线主链。

---

## 3. 与当前在线主链的关系
当前已确认的在线链分为两部分：

V2 页面主链：

`app.py -> backend/app/main.py -> backend/app/routers/actions_bridge.py -> backend/zhifei_autoplan/*`

兼容 API 链：

`backend/app/main.py -> backend/app/routers/zhifei_autoplan.py -> backend/zhifei_autoplan/*`

其中：
- `devserver.py` 为历史兼容启动壳
- `backend/app/main.py` 为 FastAPI 主入口

当前在线知识图谱运行链以以下模块为准：
- `backend/zhifei_autoplan/kg_store.py`
- `backend/zhifei_autoplan/kg_runtime.py`

当前在线知识图谱状态目录为：
- `backend/data/kg/`

截至当前体检，`v2/` 目录下逻辑**未确认接入主入口在线链**。

因此，默认将本目录标记为：
- 实验链
- 旁路链
- 候选能力链

不得直接写成当前在线主链事实。

---

## 4. 本目录检查目标
后续检查本目录时，只做以下几类判断：

### 4.1 判断能力角色
确认文件属于：
- ingestion
- graph dispatch
- multi-agent pipeline
- self-healing
- graph report
- 数据库存储/图谱落盘
- 实验性辅助逻辑

### 4.2 判断真实接入关系
必须先确认：
- 是否被 `backend/app/routers/zhifei_autoplan.py` 真实调用
- 是否被 `backend/zhifei_autoplan/orchestrator.py` 主链真实调用
- 是否只是内部自循环引用
- 是否仅供实验流程使用

### 4.3 判断是否可提升为主链候选
若未来准备把 v2 纳入主链，必须补齐证据：
- 路由挂载关系
- 编排入口调用关系
- 状态落盘目录
- 回滚方案
- 审计留痕

未满足这些条件前，不得把 v2 当成当前在线链。

---

## 5. 与 graph_dispatcher / 外部知识目录的关系
若本目录逻辑涉及：
- `graph_dispatcher`
- `multi_agent_pipeline`
- `data_graph_ingestion`
- 根目录 `knowledge_graph/`
- 根目录 `知识图谱/`

应统一标注为：
- 图谱实验处理链
- 外部资产接入链
- 离线/半在线能力链

不得直接推导为：
- 当前线上检索主链
- 当前主服务必经路径

---

## 6. 修订原则
### 6.1 先隔离，再评估
本目录的修改，优先做：
- 边界隔离
- 能力说明
- 文件归类
- 引用核对

不先做主链改造。

### 6.2 不跨链改主服务
未确认真实挂载前，不得为了整理 v2，直接改动：
- `devserver.py`
- `backend/app/main.py`
- `backend/app/routers/zhifei_autoplan.py`

### 6.3 若准备接入主链，必须单独立项
如后续要让 v2 接入主链，必须单独补齐：
- 接入方案
- 开关控制
- 回退方案
- 审计路径
- 落盘路径说明

---

## 7. 禁止事项
### 7.1 禁止误判为在线主链
禁止把本目录直接写成：
- 当前 V2 页面主链
- 当前 FastAPI 必经路径
- 当前 KG 在线检索主实现

### 7.2 禁止跳过证据直接重构
未确认调用关系前，不得基于“看起来更先进”就直接用 v2 覆盖现有主链。

### 7.3 禁止把实验数据流当生产事实
本目录中的数据库、图谱库、报告、patch、自愈链，不得默认视为生产运行事实。

---

## 8. 当前事实基线
截至当前体检，可确认：

- `v2/` 目录存在
- 与图谱处理相关
- 当前未确认接入主入口在线链
- 当前在线 KG 链仍以 `kg_store.py`、`kg_runtime.py` 为准
- 根目录 `knowledge_graph/`、`知识图谱/` 更像资产目录
- v2 当前应视为实验/旁路链

---

## 9. 默认处理策略
进入本目录后，默认按以下顺序处理：

1. 识别模块职责
2. 核对是否被主链真实调用
3. 判断是否仅被实验链使用
4. 决定是否纳入未来接入方案
5. 最后再考虑清理、归档、重构
