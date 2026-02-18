# blockers

当前无阻塞项。

## 已解决
- BLOCKER-001: goal.md 未定义具体任务 → 已定义
- BLOCKER-002: Python 依赖架构不兼容 → 已重新安装修复
- BLOCKER-003: 缺乏单元测试框架 → 已添加 pytest (2026-02-04)
- BLOCKER-004: pytest 不支持 asyncio → 已安装 pytest-asyncio 并配置 (2026-02-04)
- BLOCKER-005: compose_engine_service.py 存在 UnboundLocalError bug → 已修复 (2026-02-04)
  - 问题: tender_matrix 在第 347 行使用但在第 366 行才定义
  - 修复: 将 load_tender_matrix() 调用移到使用之前
- BUG-006: orchestrator.py 行132 存在 NoneType bug → 已修复 (2026-02-04)
  - 问题: writer.write 返回 None 时 `last.get("error")` 崩溃
  - 修复: 添加 `last and` 前置检查
- WARNING-007: matplotlib 中文字体缺失警告 → 已修复 (2026-02-04)
  - 问题: media.py 生成图表时因缺少中文字体产生 84 个警告
  - 修复: 配置 matplotlib rcParams 使用系统可用的中文字体 (STHeiti, Hiragino Sans GB 等)
- WARNING-008: google.generativeai 废弃警告 → 已迁移至 google.genai (2026-02-04)
- ISSUE-009: status.md 中 app/core 路径错误 → 已修正为 backend/app/core (2026-02-04)

## 待改进（非阻塞）
- 整体测试覆盖率 79%+，已超额达成目标 (75%)
- compose_engine_service.py (94%) ✅
- orchestrator.py (93%) ✅
- precheck_guard_service.py (100%) ✅
- project_profile_engine.py (100%) ✅
- retrieve_service.py (90%) ✅
- utils_write_docx.py (100%) ✅
- rule_engine.py (83%) ✅ (本轮新增)
- gap_analyzer.py (100%) ✅ (本轮新增)

## 低覆盖率模块（可继续优化）
- backend/app/ingest.py (0%) - 可选
- backend/app/ingest_response.py (0%) - 可选
- backend/assistants/codex_agent.py (0%) - 可选
- services/compose_engine.py (64%) - 可选
- services/kg_loader.py (63%) - 可选

## 警告（非阻塞）
- **pytest 警告数量：0** ✅ 全部消除
