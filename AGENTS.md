# AGENTS.md

## 1. 适用范围
本文件适用于本项目根目录及其默认继承的全部子目录。
如子目录存在更近层级的 `AGENTS.md`，以更近层级文件为准。

---

## 2. 项目主链判定
本项目当前在线链分为“V2 页面主链”和“兼容 API 链”两部分：

V2 页面主链：

`app.py -> backend/app/main.py -> backend/app/routers/actions_bridge.py -> backend/zhifei_autoplan/*`

兼容 API 链：

`backend/app/main.py -> backend/app/routers/zhifei_autoplan.py -> backend/zhifei_autoplan/*`

### 2.1 启动入口
- V2 页面入口：`app.py`
- FastAPI 实际启动目标：`backend.app.main:app`
- `devserver.py` 为历史兼容启动壳，不应再视为当前页面主入口

### 2.2 主服务入口
- FastAPI 主入口：`backend/app/main.py`

### 2.3 主业务路由
`backend/app/main.py` 当前挂载的主路由包括：
- `ingest_router`
- `retrieve_router`
- `publish_router`
- `score_router`
- `zhifei_autoplan_router`
- `actions_bridge_router`
- `auth_router`

其中与当前文档生成主流程直接相关的路由为：
- `backend/app/routers/actions_bridge.py`
- 路由前缀：`/actions`
- 当前 V2 页面生成、任务轮询、下载主走这里

兼容层/脚本入口仍为：
- `backend/app/routers/zhifei_autoplan.py`
- 路由前缀：`/autoplan`
- 承载 KG、审计、兼容调用等能力

---

## 3. 主链工作边界
后续检查、修订、补丁、重构、规则设计，默认优先围绕以下路径展开：

- `app.py`
- `devserver.py`
- `backend/app/main.py`
- `backend/app/routers/`
- `backend/zhifei_autoplan/`
- `backend/data/`
- `build/`

如无明确证据，不得把其他目录误判为当前在线主链。

---

## 4. 导出与审计边界
### 4.1 导出链
本项目当前导出主落盘目录为：
- `build/`

典型输出包括但不限于：
- `autoplan_generated.json`
- `autoplan_generated_v*.docx`
- compare docx
- 审计导出文件
- zip 打包结果

### 4.2 审计链
本项目当前真实审计源位于：
- `backend/data/audit/ingest.jsonl`
- `backend/data/audit/export.jsonl`

审计导出目录位于：
- `build/_audit_exports/<user_id>/`

### 4.3 审计脚本定位
以下文件属于离线审计/复核脚本，不属于在线主链：
- `check_audit.py`
- `replay_audit.py`

处理这两个文件时，应按“离线检查工具”处理，不得当成 FastAPI 在线服务入口。

---

## 5. 知识图谱在线链边界
### 5.1 在线知识图谱能力
本项目已具备在线知识图谱接口，接口能力位于 `backend/app/routers/zhifei_autoplan.py`，包括：
- `/kg/upload`
- `/kg/list`
- `/kg/active`
- `/kg/activate`
- `/kg/search`

### 5.2 在线知识图谱运行链
当前在线知识图谱运行链以以下模块为准：
- `backend/zhifei_autoplan/kg_store.py`
- `backend/zhifei_autoplan/kg_runtime.py`

当前在线知识图谱状态目录为：
- `backend/data/kg/`

典型状态文件包括：
- `kg_index.json`
- `active_kg.json`

若上述文件缺失或为空，优先判断为“尚未上传/尚未激活知识图谱”，不得直接判定为代码断链。

---

## 6. 旁路/独立能力隔离规则
以下内容当前已识别为旁路能力、实验链或独立脚本，默认不纳入当前在线主链判断：

- `routers/assist_codex.py`
- `clawdbot/`
- `clawdbot/run.sh`
- `clawdbot/supervisor_prompt.txt`
- `backend/zhifei_autoplan/v2/`
- `backend/zhifei_autoplan/graph_dispatcher.py`
- 根目录 `knowledge_graph/`
- 根目录 `知识图谱/`

处理这些路径时，必须先判断“是否被主入口真实引用”。  
在没有明确引用证据前，统一视为：
- 旁路能力
- 试验能力
- 外部知识资产目录
- 独立脚本链

不得直接把它们写入主链诊断结论。

---

## 7. 检查与修订优先级
后续所有体检、修复、规则设计，按以下优先级执行：

### 第一优先级：启动与入口一致性
检查：
- `devserver.py`
- `backend/app/main.py`
- 路由挂载关系
- 启动目标是否偏移

### 第二优先级：主路由与核心编排链
检查：
- `backend/app/routers/actions_bridge.py`
- `backend/app/routers/zhifei_autoplan.py`
- `backend/zhifei_autoplan/orchestrator.py`
- 导出链
- job 链
- 审计链

### 第三优先级：知识图谱在线链
检查：
- `/kg/*` 接口
- `kg_store.py`
- `kg_runtime.py`
- `backend/data/kg/` 状态文件

### 第四优先级：旁路能力
检查：
- `assist_codex`
- `clawdbot`
- `v2`
- `knowledge_graph`
- `知识图谱`

旁路能力只做边界识别与隔离，不抢占主链判断。

---

## 8. 修订原则
### 8.1 先判断归属，再改代码
任何修改前，先确认该文件属于：
- 在线主链
- 离线脚本
- 旁路能力
- 资产目录

未确认归属前，不直接修改。

### 8.2 先备份，再修订
涉及主链文件的修订，先做原文件备份，再执行修改。

### 8.3 一次只改一类问题
禁止一次同时修改入口、路由、导出、知识图谱、旁路脚本多类问题。
应遵循：
- 先入口
- 再主路由
- 再导出/审计
- 再知识图谱
- 最后旁路链

### 8.4 改后复检
每次修订完成后，必须重新检查：
- 启动目标
- 主路由挂载
- 审计源
- build 输出
- KG 状态文件

---

## 9. 规则设计要求
后续所有项目级规则设计，必须采用三层结构：

- 全局规则
- 项目规则
- 子模块规则

其中本文件属于：
- 项目根目录规则

后续若为以下路径补写规则，应单独下沉：
- `knowledge_graph/`
- `知识图谱/`
- `backend/zhifei_autoplan/v2/`
- `clawdbot/`

---

## 10. 禁止事项
### 10.1 禁止误判主链
禁止把以下内容直接判定为在线主链：
- `assist_codex`
- `clawdbot`
- `v2`
- `graph_dispatcher`
- `knowledge_graph/`
- `知识图谱/`

### 10.2 禁止脱离证据空写规则
新规则必须基于真实目录、真实引用、真实落盘路径编写，不得脱离代码与文件结构臆测。

### 10.3 禁止跨边界混改
不得在未确认引用关系前，把旁路目录的逻辑直接改进在线主链。

---

## 11. 当前项目事实基线
截至当前体检，已确认事实如下：

- 当前 V2 页面主链：`app.py -> backend/app/main.py -> backend/app/routers/actions_bridge.py -> backend/zhifei_autoplan/*`
- `/autoplan/*` 仍在线，但更适合作为兼容 API / KG / 审计脚本入口
- 导出主目录：`build/`
- 审计源：`backend/data/audit/*.jsonl`
- KG 在线状态目录：`backend/data/kg/`
- KG 在线接口已存在，但当前更像“未初始化/未上传/未激活”
- `check_audit.py`、`replay_audit.py` 为离线脚本
- `assist_codex`、`clawdbot`、`v2`、`knowledge_graph/`、`知识图谱/` 当前不作为在线主链判定依据
