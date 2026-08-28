# 施组编制系统全量审计报告

## 审计结论

本轮以提交 `b60dd79d2a1557f2754294082e74d1b09e459894` 为修改前基线，覆盖 FastAPI 服务、施组编排与导出、DOCX 结构门禁、实际渲染、图形生成、资料上传和自动化测试。修改前全量回归为 3242 passed、1 skipped、8 warnings；修改后为 3261 passed、1 skipped、8 warnings，失败 0。

本地可执行范围内共登记 15 项问题：P0 0、P1 12、P2 3、P3 0；15 项均已整改并有自动化或实样证据。A–E 五份 DOCX 经 LibreOffice Headless 真实渲染为 547 页，逐页指标、逐页联络图和中文逐字形门禁均通过；F 的 8 类异常资料均命中预期拒绝或冲突判定。

## 系统结构

- 服务层：`backend/app/main.py` 与 `backend/app/routers/` 提供健康检查、资料导入和施组业务接口。
- 编排层：`backend/zhifei_autoplan/` 负责章节、质量、证据、媒体和导出编排。
- 文档层：`exporter.py` 生成 OOXML；`docx_structural_quality.py` 做包结构门禁；`docx_visual_quality.py` 调用真实渲染器并检查页面像素与中文字形。
- 图形层：`engineering_graphics.py` 从同一语义模型输出 300 dpi PNG 与 SVG，并进行节点重叠、边界溢出和路由检查。
- 验收层：`scripts/generate_qa_acceptance_samples.py`、`generate_qa_abnormal_samples.py`、`build_qa_contact_sheets.py` 和 `assemble_qa_evidence.py` 形成可重复证据链。

## 主要根因

1. Word 规则散落在直接格式、命名样式和 XML 操作中，缺少统一的精确值与包级门禁。
2. 宽表和横向节只覆盖基础场景，未管理节切换后的页眉页脚关系及额外分页。
3. 旧图形路径侧重“能生成图片”，没有同源 SVG、物理尺寸、有效 DPI 和几何安全回执。
4. 视觉检查曾把页面方向写死为纵向，且仅看文本无法发现字体缺失、空恢复页和横向故事部件丢失。
5. 上传链路虽然分块写入，但缺少显式大小上限、批内内容去重和损坏文件的可解释拒绝。

## 整改结果

- 宋体、黑体、仿宋体均以准确中文别名写入 `ascii/hAnsi/eastAsia/cs`，正文 14 pt、固定 22 pt、首行 2 字符、段前段后 0。
- 标题、题注、表格、目录、页眉页脚和页码统一纳入字号、同页和故事部件检查。
- DOCX 保存改为临时文件、净化包和原子替换；清除隐私元数据/customXml，验证 XML、relationships、书签和修订标签。
- 新增 12 列以内结构化表、合并表头、嵌套表、重复表头、禁跨页行和 A4 横纵向分节。
- 每个后续节显式物化 default/first/even 页眉页脚；修复横向恢复空页与连续页码。
- 图形输出固定为 26.0 cm × 15.7 cm、3071 × 1854 px、300 dpi，并保留 SVG 源。
- 图片低于 150 dpi 阻断，150–299 dpi 警告；必需图片缺失、损坏或重复时 fail-closed。
- 上传资料超过默认 100 MiB 返回 413；损坏解析返回 422；空文件返回 400；批内重复按 SHA-256 拒绝。

## 验证边界

Microsoft Word 和 WPS 在当前环境中不可用，因此未声称完成两款商业软件的原生打开/另存验证。替代证据为 LibreOffice Headless、OOXML 包级验证、547 页像素渲染、中文逐字形检查和代表性全分辨率人工复核。所有验收数据均为合成数据，不代表真实项目事实或生产部署状态。

静态 `p0_readiness.py` 返回 `NO-GO_P0_READINESS_STATIC`，唯一原因是 `worktree_not_clean`；这是未提交审计成果和用户原有改动存在时的发布前置条件，不是运行时 P0。受控 FastAPI 启动及 `/health` 已通过，退出后端口已释放。
