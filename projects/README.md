# projects 目录用法（无人值守批量编制）

目录结构：
- `projects/inbox/`：把每个项目放一个子文件夹，文件拷贝完成后脚本会自动接管
- `projects/work/`：处理中（自动移动）
- `projects/done/`：成功（自动移动）
- `projects/failed/`：失败（自动移动，保留日志与结果）

每个项目文件夹建议包含：
- 招标文件：文件名包含 `招标/补遗/澄清/答疑/tender`（PDF/DOCX 优先）
- 工程量清单：文件名包含 `清单/工程量清单/boq/报价/计价`（Excel 优先）
- 图纸/企业标准/工法/作业指导：直接放进来即可（会入库并生成证据定位符）
- 可选：LOGO 文件（文件名包含 `logo/标志/标识/徽标`），系统会优先使用你提供的版本
- 可选：`project.json`（复制 `projects/_template/project.json` 改字段）
- 可选：`plan.json`（覆盖目录/版式/页数等要求；会调用 `/actions/plan/save` 绑定到本次 `project_id`）

脚本：
- 入口：`/Users/youfeini/Desktop/文档生成系统/scripts/watch_projects_autoplan.py`
- 输出：每个项目会在 `projects/done/<project_id>/` 或 `projects/failed/<project_id>/` 生成：
  - `autoplan_<project_id>.json`
  - `autoplan_<project_id>_v1.docx`（若 variants>1，会生成 v2/v3...）
  - `autoplan_<project_id>_compare_v1.docx`
  - `autoplan_<project_id>_focus_v1.xlsx`（重点清单项闭环 + 问题清单 + 自动修订建议）
  - `run_summary.json`（hard gate 结果）

质量门禁（硬门禁，失败会进 failed）：
- 禁止官话/套话/空话
- 风险必须三元组 `风险→控制→验证`
- 质量/安全/文明环保章节必须闭环（含记录/台账 + 偏差处置）
- 量化指标必须有单位数值
- 证据可追溯定位符（入库资料存在时）
- 重点清单项必须绑定图纸/标准证据（入库资料存在时）

可编辑入口（不改代码）：
- `project.json`：
  - `project_id`：固定项目ID（可选）。用于重复跑同一项目时复用：证据入库、LOGO/品牌锁定、plan 默认值绑定
  - `requirements`：全局编制约束（会传入 `/actions/generate_async`）
  - `plan` 或 `plan.json`：覆盖目录/章内要求/每章页数/字号行距等（会保存为本次 `project_id` 的计划默认值）
  - `params_override`：本次生成的量化默认值覆盖（例如 PM10/噪声阈值、抽检频次等），不写入全局 `backend/data/autoplan/params.json`
- `backend/data/autoplan/logic_templates.json`：A/B/C 章内逻辑模版（不改变招标目录，只控制章内推理结构）
- `backend/data/autoplan/four_new_tech_library.json`：四新技术可编辑库（按清单/工序匹配推荐，输出必须可验收闭环）
