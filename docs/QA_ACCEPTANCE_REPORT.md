# QA 验收报告

## 自动化与运行结果

| 命令 | 结果 |
|---|---|
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD" .venv/bin/python -m pytest -q` | 3261 passed，1 skipped，0 failed，8 warnings，58.98 s |
| `... pytest ...test_portrait_restore... test_engineering_graphics.py` | 14 passed |
| `... pytest -q backend/tests/test_ingest_upload_streaming.py` | 4 passed |
| `... generate_qa_acceptance_samples.py` | A–E DOCX 生成及结构门禁通过 |
| `... generate_qa_abnormal_samples.py` | F 的 8/8 异常类别命中 |
| `... uvicorn ... --port 18765` + `curl /health` | `ok=true`；正常退出；端口释放 |
| `... p0_readiness.py --json` | 退出 1；唯一失败 `worktree_not_clean`，为未提交成果的发布前置条件 |

8 条 warning 均来自 passlib/ezdxf 依赖的弃用提示，不是测试失败。唯一 skipped 为既有 V2 数据图条件性测试。

## 实样结果

| 样本 | 页数 | 节 | 表 | 图 | 横向页 | 结构 | 真实渲染 |
|---|---:|---:|---:|---:|---|---|---|
| A 普通施组 | 29 | 1 | 5 | 6 | 无 | pass | pass |
| B 大型施组 | 219 | 3 | 41 | 30 | 194–204 | pass | pass |
| C 200 页限制 | 193 | 1 | 7 | 0 | 无 | pass | pass |
| D 图形密集 | 32 | 1 | 4 | 9 | 无 | pass | pass |
| E 复杂表格 | 74 | 2 | 9 | 0 | 47–74 | pass | pass |

合计 547 页、45 图。五份文档均为：空白页 0、孤标题页 0、边缘裁切风险页 0、中文逐字形状态 pass。每份仅第 2 页目录被记为允许预算内的稀疏页。PDF 页数与高分辨率 PNG 数逐份一致，所有页面均进入联络图。

## 视觉复核

- 自动：对 547 页逐页计算文本量、墨迹率、边缘墨迹、空白、稀疏、孤标题和裁切风险；每份抽取 3000 个中文字符检查实际字形位图。
- 全页覆盖：38 张联络图覆盖全部 547 页。
- 全分辨率重点：D 第 29–30 页，E 第 49/61/74 页，B 第 194–204 页横向表格和第 205–219 页图形。
- 发现并修复：E 横向续页页眉页脚丢失；B 横向恢复后出现仅页眉页脚空页。最终回执均无硬失败。

## 异常资料 F

中文文件名、空文件、损坏 PDF、内容重复、2 MiB 超限边界样本、声明 2 页实际 1 页、工期 180/210 冲突、外部项目名称残留共 8 类全部检出。生产上传控制返回 400/413/422，并在成功批次中返回 `rejected` 明细。

## 判定

本地可执行整改与验收状态为 pass，P0/P1 已发现问题为 0 个未解决。Microsoft Word/WPS 原生打开、另存和打印仍为外部商业软件验证项，状态为 NOT_DETERMINED，不能用 LibreOffice 结果替代宣称。
