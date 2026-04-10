# AGENTS.md

## 1. 适用范围
本文件适用于 `知识图谱/` 目录及其默认继承的子目录。
如更下层存在新的 `AGENTS.md`，以更近层级规则为准。

---

## 2. 目录角色定义
`知识图谱/` 目录在当前项目中，默认按以下角色理解：

- 知识图谱资产目录
- 图谱文件目录
- 图谱中间结果目录
- 图谱离线整理目录
- 图谱实验资料目录

本目录不是当前 FastAPI 在线主入口。  
本目录不是当前在线知识图谱检索主链的直接等价物。

---

## 3. 与项目在线主链的关系
当前项目在线主链已确认：

V2 页面主链：

`app.py -> backend/app/main.py -> backend/app/routers/actions_bridge.py -> backend/zhifei_autoplan/*`

兼容 API 链：

`backend/app/main.py -> backend/app/routers/zhifei_autoplan.py -> backend/zhifei_autoplan/*`

其中：
- `devserver.py` 为历史兼容启动壳
- `backend/app/main.py` 为 FastAPI 主入口

当前在线知识图谱接口位于：
- `backend/app/routers/zhifei_autoplan.py`

当前在线知识图谱运行链以以下模块为准：
- `backend/zhifei_autoplan/kg_store.py`
- `backend/zhifei_autoplan/kg_runtime.py`

当前在线知识图谱状态目录为：
- `backend/data/kg/`

因此，处理 `知识图谱/` 目录时，必须区分：

### 3.1 在线运行链
- `/kg/upload`
- `/kg/list`
- `/kg/active`
- `/kg/activate`
- `/kg/search`
- `backend/data/kg/`
- `kg_store.py`
- `kg_runtime.py`

### 3.2 资产/实验/离线目录
- `知识图谱/`
- 根目录 `knowledge_graph/`
- `backend/zhifei_autoplan/v2/`
- graph dispatcher 相关实现
- 图谱 ingestion / pipeline / 报告生成类文件

不得把资产目录直接等同于在线检索主链。

---

## 4. 检查本目录时的优先目标
后续检查 `知识图谱/` 目录时，默认只做以下几类判断：

### 4.1 判断文件角色
确认文件属于哪一类：
- 原始知识图谱文件
- 中间处理结果
- compliance 类规则结果
- catalog / summary 类汇总文件
- 样例数据
- 实验性输出

### 4.2 判断与在线链是否存在真实引用
检查时必须先回答：
- 是否被 `backend/zhifei_autoplan/*` 真实引用
- 是否只被 v2 / graph dispatcher / pipeline 引用
- 是否完全未被当前主链引用

### 4.3 判断是否为“资产来源”而不是“在线状态”
若文件只是知识来源、离线成果、补丁素材、目录索引，则应标注为：
- 资产来源
- 离线图谱
- 辅助知识文件

而不是：
- 在线检索状态文件
- 当前运行态主索引

---

## 5. 本目录与 backend/data/kg 的边界
必须明确区分以下两类目录：

### 5.1 `知识图谱/`
含义：
- 图谱资产
- 图谱原件
- 图谱中间产物
- 离线图谱文件

### 5.2 `backend/data/kg/`
含义：
- 当前在线知识图谱状态目录
- 在线上传后的索引/激活状态
- 在线检索直接读取的状态文件

处理规则：
- 不得把 `知识图谱/` 中的文件直接当成 `backend/data/kg/` 在线状态文件
- 不得因为 `知识图谱/` 非空，就推断在线 KG 已初始化
- 也不得因为 `backend/data/kg/` 为空，就认定 `知识图谱/` 无价值

---

## 6. 修订与整理原则
### 6.1 先识别，再整理
整理本目录前，先区分：
- 资产文件
- 在线状态文件
- 离线生成物
- 实验脚本输出
- 可清理临时文件

### 6.2 不跨目录修改主链
除非已确认真实引用关系，否则不得为了整理 `知识图谱/`，直接改动：
- `backend/app/main.py`
- `backend/app/routers/zhifei_autoplan.py`
- `backend/zhifei_autoplan/kg_store.py`
- `backend/zhifei_autoplan/kg_runtime.py`

### 6.3 先备份，再清理
如果要删除、合并、移动本目录内文件，先做备份或清单记录。

### 6.4 只做证据化整理
所有整理动作必须基于：
- 实际引用关系
- 文件内容
- 文件生成来源
- 文件落盘路径

不得凭名称臆测后批量清理。

---

## 7. 规则设计要求
后续若在本目录继续下沉规则，建议按以下层次拆分：

- 图谱原始资产规则
- compliance 规则文件规则
- catalog / summary 汇总文件规则
- 临时生成物清理规则

本文件仅负责：
- 定义目录角色
- 划清与在线主链边界
- 防止误判

---

## 8. 禁止事项
### 8.1 禁止误判为在线主链
禁止把 `知识图谱/` 目录直接写成：
- 当前 FastAPI 主入口
- 当前在线知识图谱唯一来源
- 当前在线检索直接读取目录

### 8.2 禁止跳过引用分析
未确认真实引用关系前，不得将本目录文件直接并入主链修复方案。

### 8.3 禁止把 v2 结论强行覆盖到主链
若某些图谱处理逻辑只存在于：
- `backend/zhifei_autoplan/v2/`
- graph dispatcher
- multi agent pipeline

则应标注为：
- v2 / 实验链 / 旁路链

不得直接写成当前在线主链事实。

---

## 9. 当前事实基线
截至当前体检，可确认：

- `知识图谱/` 属于知识图谱相关目录，但不是已确认的在线主链入口
- 当前在线知识图谱接口在 `backend/app/routers/zhifei_autoplan.py`
- 当前在线知识图谱运行链以 `kg_store.py`、`kg_runtime.py` 为准
- 当前在线知识图谱状态目录为 `backend/data/kg/`
- `backend/data/kg/` 当前更像“尚未上传/尚未激活”
- `v2`、graph dispatcher、外部“知识图谱”目录当前未确认接入主入口在线链

---

## 10. 本目录的默认处理策略
后续工具或人员进入本目录时，默认按以下顺序处理：

1. 先识别文件类别
2. 再判断是否被主链引用
3. 再判断是否被 v2 / 实验链引用
4. 再决定是否纳入修订范围
5. 最后再做清理、归档、补规则
