
# 专业级可追溯文档自动化生成系统 · API 设计规范（V1）

## 1. 概述
本文件定义系统四大核心端点：/ingest、/retrieve、/compose、/export 的参数、响应格式与执行逻辑，用于支撑 SuperKG-FullPlus3.1 + Prompt V3.1 + Final Master Command 3.1 的全链路施工组织设计自动化生成。

## 2. API 总览
- POST /ingest  —— 文件上传与解析
- POST /retrieve —— 多源检索（BM25 + 向量检索）
- POST /compose —— 自动组稿（施组生成）
- POST /export —— Word/PDF 导出

---

## 3. /ingest
### 功能
加载以下文件并解析：
- SuperKG-FullPlus3.1.json
- Prompt V3.1
- 招标文件（PDF/Docx）
- 图纸（PDF）
- 工程量清单（Excel）
- 答疑文件

### 请求参数
```
{
  "files": {
    "kg": "SuperKG-FullPlus3.1.json",
    "prompt": "Prompt-V3.1.docx",
    "tender_docs": [...],
    "drawings": [...],
    "bill": "清单.xlsx",
    "qa": [...]
  }
}
```

### 响应
```
{
  "status": "ok",
  "parsed": {
     "kg_nodes": 12892,
     "tender_sections": 42,
     "drawings": 120,
     "bill_items": 856
  }
}
```

---

## 4. /retrieve
### 功能
对输入内容进行高精度检索，支持：
- BM25（精确匹配）
- 向量检索（语义召回）
- 图谱节点检索（工序/规范/图纸索引）

### 请求
```
{
  "query": "钢筋保护层控制要求",
  "top_k": 10
}
```

### 响应
```
{
  "results": [
    {"source": "SuperKG", "text": "...", "score": 0.92},
    {"source": "Tender", "text": "...", "score": 0.88}
  ]
}
```

---

## 5. /compose
### 功能
生成完整 19 章施工组织设计。

### 内置规则
- 必须按招标目录生成
- 内容补齐（来自 SuperKG）
- 工序级15~20字段写作
- 页数限制控制（Prompt V3.1）
- 章节伸缩与评分权重分配
- 可追溯性索引生成

### 请求
```
{
  "project_id": "A001",
  "max_pages": 50
}
```

### 响应
```
{
  "status": "ok",
  "sections": [...],
  "trace_index": [...]
}
```

---

## 6. /export
### 功能
输出 Word/PDF

### 请求
```
{
  "project_id": "A001",
  "format": "docx"
}
```

### 响应
```
{
  "file": "/exports/A001.docx"
}
```

---

## 7. 错误码
- 400：文件缺失
- 422：解析失败
- 500：生成失败

---

# 结束
