# Custom GPT Actions 接入说明

## 1. 后端配置

在服务启动前设置 `X-Actions-Key` 对应环境变量：

```bash
export ZF_ACTIONS_KEY="your-very-strong-key"
export PYTHONPATH="$PWD:$PYTHONPATH"
python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

## 2. Custom GPT 中导入 Actions

1. 打开 GPT Builder -> `Configure` -> `Actions`。
2. 导入 OpenAPI：
   - 文件：`/Users/youfeini/Desktop/文档生成系统/docs/custom_gpt_actions_openapi.json`
3. 认证方式选 `API Key`：
   - Header 名称：`X-Actions-Key`
   - Key 值：与 `ZF_ACTIONS_KEY` 一致。
4. 把 `servers.url` 改成你真实可访问的后端域名（HTTPS）。

## 3. 推荐调用顺序

1. `POST /actions/tender/parse`：上传并解析招标文件（可多个文件）。
   - 返回的 `matrix` 会包含：
     - `outline`：从招标文本抽取的章节目录（抽取不到会给“最小覆盖兜底目录”）
     - `style`：从招标抽取的版式要求（字体/字号/行距/纸张/页边距等）
     - `chapter_pages` / `chapter_requirements` / `global_requirements`：页数与条款约束（若能抽取到）
   - 多项目并行/批量编制建议：给 `tender/parse` 追加 query 参数 `project_id`，并在后续 `boq/parse`、`/ingest/upload`、`generate_async` 传入同一 `project_id`，避免数据互相覆盖。
2. `POST /actions/boq/parse`：上传并解析工程量清单（xlsx/xls/pdf）。
   - 多项目并行/批量编制建议：给 `boq/parse` 追加 query 参数 `project_id`，与招标/证据/生成保持一致。
3. （可选）`POST /ingest/upload`：上传图纸/技术资料到证据库，用于生成时引用证据片段。
   - 建议同时上传投标公司 LOGO（文件名含 `logo/标志/标识/徽标`），系统会自动打 `logo` 标签，后续生成思维导图/插图时可自动带上。
   - 批量编制/证据隔离建议：给 `/ingest/upload` 追加 query 参数 `project_id`，并在后续 `generate_async` 传入同一 `project_id`。
4. `POST /actions/plan/save`（可选）：把 `tender/parse` 返回的 `outline/style/chapter_pages/chapter_requirements` 保存为默认值，便于后续多次生成复用。
   - 若你要“按项目隔离保存 plan.json”，给 `plan/save` 增加 query 参数 `project_id`。
5. `POST /actions/generate_async`：提交任务（推荐；可选字段 `project_id` 用于证据隔离）。
6. `GET /actions/job_status?job_id=...`：轮询直到 `status=done`。
7. `GET /actions/result?job_id=...&variant=1`：读取质量检查、问题清单、自动修订建议。
8. `GET /actions/download?job_id=...&kind=docx&variant=1`：下载成品 DOCX（也可 `compare_docx/json`）。
   - 重点项闭环清单（XLSX）：`GET /actions/download?job_id=...&kind=focus_xlsx&variant=1`

如果你希望“由 ChatGPT 在对话里写正文（不用任何模型 API）”，只把校验与导出交给后端：

1. 你在对话里写出 `sections`（title+content）。
2. `POST /actions/quality_check`：得到“问题清单 + 自动修订建议”。
3. 你按建议修订后，`POST /actions/export_docx`：生成 `job_id`，再用 `GET /actions/download` 下载 DOCX。

## 4. 文风硬约束（已内置）

系统已启用“硬门禁”：

- 禁止官话/套话/空话表达。
- 命中词会进入高优先级问题项并触发自动改写。
- 输出内容强制量化与可验证闭环（风险→控制→验证）。
- 证据标注禁止使用“待补充/待定位/TBD”，需写成“【证据:文件名#p页_sha@offset】”（可追溯定位符）。
- **章节结构蓝图**：当章节标题匹配蓝图条目（例如“对工程项目整体理解与实施路径”），系统会强制该章出现指定锚点小标题（例如“工程特点/总体部署”），并给出对应的章内编制要点（不改变招标目录，只约束章内结构）。蓝图配置文件：`backend/data/autoplan/chapter_blueprints.json`。
- 若项目入库了“企业标准/工法/作业指导”等资料（tag=standard），关键工序章节必须引用至少 1 条标准证据定位符（避免只写“按标准执行”）。
- 若项目入库了图纸（tag=drawing）与企业标准（tag=standard），**重点清单项控制卡**要求同时包含：
  - 图纸定位符（用于做法/尺寸/标高校核）
  - 标准定位符（用于条款对照与验收）

## 5. 思维导图/插图（Gemini Nano Banana）

系统会在 `generate_images=true` 时，追加 1 张“施工组织设计思维导图”插图：
- 优先使用 Gemini 原生图片模型（Nano Banana）生成；未配置 Key 时回退为自动绘制版本。
- 若你提供了 LOGO（上传或 `logo_url`），思维导图会尽量把 LOGO 放在右上角。

可在 `POST /actions/generate(_async)` 或 `POST /actions/export_docx` 里传参：
- `image_provider`: `google`
- `image_model`: `gemini-2.5-flash-image`（或别名 `banana`）
- `image_api_key`: 你的 Gemini API Key（也可用环境变量 `ZF_GOOGLE_API_KEY`/`GEMINI_API_KEY`）
- `bidder_company`: 投标单位名称（用于自动尝试从公开来源解析 LOGO）
- `bidder_domain`: 投标单位官网域名（用于尝试获取更接近“标准版”的 LOGO，例如 `company.com`）
- `logo_url`: 直接指定 LOGO 图片 URL（优先级最高）
- LOGO 稳定性：如果你在编制链路里使用了同一个 `project_id`，系统会把已解析到的 LOGO 固定到项目侧配置（`backend/data/autoplan/projects/<project_id>/branding.json`），后续复跑优先复用，避免“误抓/漂移”。若需替换，优先传 `logo_url` 或上传新 LOGO 文件后重新 ingest。

## 6. 量化参数（可编辑）

系统内置参数注册表：`backend/data/autoplan/params.json`。你也可以通过 Actions 直接读写：

1) 读取当前参数：
- `GET /actions/params/get`

2) 更新参数（只改你传入的字段，其它不动）：
- `POST /actions/params/set`
  - 返回会附带 `diff`（若存在最近一次参数回执）

3) 预览差异清单（不落盘）：
- `POST /actions/params/diff`

4) 读取最近一次参数回执（参数键→出现位置→影响章节）：
- `GET /actions/params/receipt/get`
  - 多项目并行建议：给 `params/receipt/get` 增加 query 参数 `project_id`，读取对应项目的回执。
  - `params/set` 与 `params/diff` 也支持 query 参数 `project_id`，用于基于对应项目回执生成“影响章节差异清单”。

示例（把“抽检频次”改为每 50m2 1 次）：
```json
{
  "update": {
    "boq_focus_card": {
      "抽检频次": "每50m2 1次"
    }
  },
  "merge": true
}
```

## 7. 成品 DOCX 的“可追溯附录”（自动生成）

系统在导出 DOCX 时，会追加这些附录（用于评审追溯与快速定位缺口）：
- 图纸证据索引（章节-图纸绑定）
- 企业标准证据索引（章节-标准绑定）
- 重点项证据闭环索引（重点项 -> 落位章节 -> 图纸定位/标准定位 -> 闭环缺口）
- 可编辑参数影响回执（参数键 -> 影响章节）

同时会生成 1 份可直接评审的 Excel：
- `focus_xlsx`：重点项闭环清单（含：闭环OK/缺口/图纸定位/标准定位/问题清单/自动修订建议）
