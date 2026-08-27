# 当前架构与数据流

## 运行架构

```text
资料上传 / 项目输入
        │
        ▼
FastAPI routers ── 资料大小、解析、SHA-256 去重
        │
        ▼
施组编排与质量检查 ── 章节、证据、参数、媒体
        │
        ├──────────────┐
        ▼              ▼
DOCX exporter    Engineering graphics
        │          ├─ 300 dpi PNG
        │          └─ SVG
        ▼
原子净化保存
        │
        ├─ structural quality：OOXML/样式/关系/节/媒体
        ▼
LibreOffice Headless → PDF → 逐页 PNG
        │
        └─ visual quality：空白/稀疏/孤标题/裁切/CJK 字形
```

## 文档流

`export_autoplan_docx` 先净化输入并执行本地适配器导出门禁，再准备投标人可见章节、筛选媒体并计算布局。正文、Markdown 表和结构化表进入统一样式系统；宽表触发 A4 横向节，节引用显式物化。媒体按章节或文末插入并生成可追溯图清单。保存阶段清理属性与 customXml，写临时包、验证后原子替换。

结构门禁读取最终包而非内存对象，检查所有 XML 和 `.rels`、重复关系 ID、悬空目标、书签、字段、隐藏文本、修订批注、页面几何、字体段落、表格属性、图片和页眉页脚引用。结构通过后才进入真实渲染。

## 图形流

业务数据转为 `GraphicSpec`；布局器按节点数和指定模式计算行、图框、文字行与边路由；几何校验通过后，PNG/SVG 使用同一坐标和文本生成。媒体门禁记录像素、纵横比、动态范围、感知哈希、有效 DPI 与 SHA-256。DOCX 保存后再把预期媒体哈希与 `word/media` 实际哈希反向比对。

## 证据流

A–E 输入 JSON → DOCX + build/structural/figure 回执 → LibreOffice PDF → 逐页 PNG → visual 回执 → 联络图 → `acceptance_manifest.json`。F 生成独立异常文件和 `abnormal_input_receipt.json`。`assemble_qa_evidence.py` 验证页数、图数、结构、渲染和哈希后生成总清单，并把 A 样本复制到 `artifacts/qa/after`。

## 安全与边界

- 上传路径只取文件 basename；流式读取每块 1 MiB，默认总量上限 100 MiB。
- 所有验收资料为合成数据；脚本不读取密钥、不调用外部模型、不进行远端写入。
- 实际生产数据、外部模型、Word/WPS、真实打印和多人并发不在本轮本地证据范围内。
