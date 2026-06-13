# LOCAL-LAUNCHER-040 ZDoc Local App V1 Ollama Model Selection Execution Gate

## 1. 节点基本信息

节点名称：

`LOCAL-LAUNCHER-040-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-SELECTION-EXECUTION-GATE`

本节点性质：

`Ollama model selection execution gate based only on recorded local inventory`

本节点目标：

在不执行任何 Ollama 命令、不运行模型、不输入 prompt、不读取真实数据的前提下，仅基于 038 已记录的 8 个本地模型名称提出 ZDoc 场景下的模型选择建议。

本节点不是模型运行节点，不是 trial 节点，不触发 generation/export/write-back。

## 2. 用户授权摘要

用户明确授权 `LOCAL-LAUNCHER-040` 执行 Ollama model selection execution。

授权范围仅限：

1. 仓库路径确认。
2. 当前分支确认。
3. HEAD/tag 确认。
4. 工作区 clean 确认。
5. 只读复核 037 Ollama model inventory `PASS`。
6. 只读复核 038 inventory result closed。
7. 基于 038 已记录的 8 个本地模型名称进行模型选择分析。
8. 按用途提出默认通用模型、编码/工程辅助模型、大模型高质量候选、轻量快速候选、备选模型建议。
9. 说明每个候选模型适合的 ZDoc 场景。
10. 说明后续模型运行前仍需单独授权。

本节点严格禁止执行 `ollama list`、`ollama run`、`ollama pull`、`ollama serve`、`ollama create`、`ollama rm`、`ollama cp` 或任何 Ollama 模型命令，禁止任何模型推理、prompt 输入、模型下载、模型删除、模型创建，禁止读取真实 KG、真实项目资料、真实招标文件、隐私数据、`.env`、secrets、tokens、credentials、registration、metadata、proof、manifest、sample 实例、output/job/export 正文或日志正文，禁止触发 generation/export/write-back，禁止写 output/job/export，禁止进入 trial、真实使用、50 人正式使用或下一节点。

## 3. 当前基线 HEAD/tag

- 开始前 HEAD：`49a89e80246f33a151cbbe1971ce5aba233c75b4`
- 开始前 tag：`v0.1.675-local-launcher-zdoc-local-app-v1-ollama-model-selection-authorization-gate`
- 当前分支：`main`
- 上一节点：`LOCAL-LAUNCHER-039-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-SELECTION-AUTHORIZATION-GATE`

实际最近提交：

```text
49a89e8 LOCAL-LAUNCHER-039 ollama model selection authorization
```

## 4. 仓库路径确认结果

实际路径：

```text
/Users/youfeini/Desktop/文档生成系统
```

结论：符合预期仓库路径。

## 5. 当前分支确认结果

实际分支：

```text
main
```

结论：符合预期分支。

## 6. HEAD/tag 确认结果

实际开始前 HEAD：

```text
49a89e80246f33a151cbbe1971ce5aba233c75b4
```

实际开始前 HEAD tag：

```text
v0.1.675-local-launcher-zdoc-local-app-v1-ollama-model-selection-authorization-gate
```

结论：HEAD/tag 与 039 基线一致。

## 7. 工作区 clean 确认结果

开始前 `git status --short` 无输出。

结论：工作区 clean。

## 8. 037 Ollama model inventory PASS 复核结果

已只读复核：

`docs/zdoc-local-launcher-v1-ollama-model-inventory-execution-gate-local-launcher-037.md`

复核结果：

1. 037 节点性质为 Ollama model inventory execution gate only。
2. 037 在其授权范围内仅执行 1 次 `ollama list`。
3. 037 `ollama list` 退出码为 `0`。
4. 037 本地模型清单非空。
5. 037 本地模型数量为 8 个。
6. 037 未执行模型运行。
7. 037 未执行模型推理。
8. 037 未输入 prompt。
9. 037 未下载、删除、创建模型。
10. 037 未读取真实 KG / 真实项目资料。
11. 037 未触发 generation/export/write-back。
12. 037 判定为 `PASS`。

037 当前 decision 可复核：

```text
LOCAL-LAUNCHER-037 ZDOC LOCAL APP V1 OLLAMA MODEL INVENTORY EXECUTION GATE PASSED / OLLAMA MODEL INVENTORY CONFIRMED / LOCAL MODEL LIST RECORDED WITHOUT MODEL RUN / NO PROMPT INPUT / NO MODEL DOWNLOAD / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED
```

## 9. 038 inventory result closed 复核结果

已只读复核：

`docs/zdoc-local-launcher-v1-ollama-model-inventory-result-record-gate-local-launcher-038.md`

复核结果：

1. 038 节点性质为 Ollama model inventory result record only。
2. 038 记录并复核 037 Ollama model inventory 结果。
3. 038 未执行 `ollama list`。
4. 038 未运行模型。
5. 038 未输入 prompt。
6. 038 未触发 generation/export/write-back。
7. 038 记录本地模型数量为 8 个。
8. 038 记录模型清单非空。
9. 038 当前 decision 为 inventory result closed。

038 当前 decision 可复核：

```text
LOCAL-LAUNCHER-038 ZDOC LOCAL APP V1 OLLAMA MODEL INVENTORY RESULT RECORD GATE COMPLETED / OLLAMA MODEL INVENTORY PASS RECORDED / LOCAL MODEL INVENTORY RESULT CLOSED / NO ADDITIONAL OLLAMA LIST EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO MODEL DOWNLOAD / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED
```

## 10. 039 model selection authorization boundary 复核结果

已只读复核：

`docs/zdoc-local-launcher-v1-ollama-model-selection-authorization-gate-local-launcher-039.md`

复核结果：

1. 039 节点性质为 Ollama model selection authorization boundary and user authorization request only。
2. 039 明确未来 040 可基于 038 已记录的 8 个本地模型名称进行模型选择分析。
3. 039 明确未来 040 可提出默认通用模型、编码/工程辅助模型、大模型高质量候选、轻量快速候选、备选模型建议。
4. 039 明确未来 040 应说明每个候选模型适合的 ZDoc 场景。
5. 039 明确后续模型运行前仍需单独授权。
6. 039 明确未来 040 不授权任何 Ollama 命令、模型运行、prompt、真实数据读取、trial、generation/export/write-back。

039 当前 decision 可复核：

```text
LOCAL-LAUNCHER-039 ZDOC LOCAL APP V1 OLLAMA MODEL SELECTION AUTHORIZATION GATE COMPLETED / OLLAMA MODEL SELECTION EXECUTION AUTHORIZATION BOUNDARY DOCUMENTED / USER AUTHORIZATION TEMPLATE ISSUED / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO MODEL DOWNLOAD / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED
```

## 11. 模型选择依据

本节点模型选择依据仅限 038 已记录的 8 个本地模型名称：

1. `qwen3:30b`
2. `qwen3.6:35b`
3. `qwen3-next:80b-a3b-instruct-q8_0`
4. `qwen3-coder:30b`
5. `deepseek-r1:32b`
6. `qwen3:14b`
7. `qwen3:8b`
8. `qwen3:0.6b`

本节点未重新执行 `ollama list`，未读取模型文件，未加载模型，未运行 benchmark，未进行 prompt 试验。以下建议仅基于模型名称、尺寸层级和 ZDoc 当前治理链需求作静态选择。

## 12. 默认通用模型建议

默认通用模型建议：

`qwen3:30b`

理由：

1. 该模型在 038 清单中属于中高规格本地模型。
2. 相比 `qwen3-next:80b-a3b-instruct-q8_0`，更适合作为后续受控运行的第一默认候选，资源风险更低。
3. 相比 `qwen3:8b`、`qwen3:14b` 和 `qwen3:0.6b`，更适合作为 ZDoc 文档生成、结构化说明、节点回报草稿等通用文本任务的默认质量基线。

适合的 ZDoc 场景：

1. 本地文档生成系统的通用问答。
2. 节点说明、状态摘要、边界说明的草稿生成。
3. 非真实数据、非正式 trial 前的模拟文档任务。
4. 施工组织设计类长段落的初步结构化生成。

限制：

1. 本节点不验证实际生成质量。
2. 后续如需运行 `qwen3:30b`，必须另设模型运行授权门。

## 13. 编码 / 工程辅助模型建议

编码 / 工程辅助模型建议：

`qwen3-coder:30b`

理由：

1. 模型名称明确指向 coding / engineering 用途。
2. 适合作为后续 ZDoc 本地 App、配置、脚本、错误信息解释等工程辅助场景的优先候选。
3. 规格层级与 `qwen3:30b` 接近，可作为通用模型之外的专项模型。

适合的 ZDoc 场景：

1. 本地启动器命令解释。
2. 配置片段和错误信息分析。
3. backend/frontend/config 相关问题的只读解释。
4. 未来若获授权，可用于工程辅助类 prompt 的受控验证。

限制：

1. 本节点未运行模型。
2. 本节点未读取 backend/frontend/config 内容。
3. 后续任何代码相关模型运行仍需单独授权。

## 14. 大模型高质量候选建议

大模型高质量候选建议：

1. `qwen3-next:80b-a3b-instruct-q8_0`
2. `qwen3.6:35b`

理由：

1. `qwen3-next:80b-a3b-instruct-q8_0` 在 038 清单中尺寸最大，适合作为高质量候选，但资源和耗时风险最高。
2. `qwen3.6:35b` 规格高于 30b 层级，可作为高质量候选的次优先选项。
3. 两者更适合在后续明确资源、超时、失败回退和终止条件后再进入模型运行授权。

适合的 ZDoc 场景：

1. 长文档章节重写。
2. 复杂施工组织设计文本的结构化优化。
3. 多约束说明文本生成。
4. 未来模拟样本上的高质量候选对比。

限制：

1. 本节点不判断实际速度、显存、内存或稳定性。
2. 本节点不执行 benchmark。
3. 后续如需运行任一大模型，必须另设模型运行授权门，并明确超时、资源和中止条件。

## 15. 轻量快速候选建议

轻量快速候选建议：

1. `qwen3:0.6b`
2. `qwen3:8b`

理由：

1. `qwen3:0.6b` 在 038 清单中尺寸最小，适合未来受控运行时作为连接性或最小 smoke test 候选。
2. `qwen3:8b` 比 0.6b 更适合作为快速交互和低资源验证候选。
3. 两者适合先验证调用链、错误处理和响应形态，不适合作为最终质量基线。

适合的 ZDoc 场景：

1. 未来 Ollama 调用链最小验证。
2. UI 或本地控制台响应通路 smoke test。
3. 非正式、非真实数据的短文本模拟任务。
4. 快速失败诊断和回归确认。

限制：

1. 本节点不授权任何 smoke test。
2. 后续即使只运行轻量模型，也必须另设模型运行授权门。

## 16. 备选模型建议

备选模型建议：

1. `qwen3:14b`
2. `deepseek-r1:32b`

理由：

1. `qwen3:14b` 可作为 `qwen3:30b` 的资源更低备选。
2. `deepseek-r1:32b` 可作为推理类或复杂分析类候选，但本节点不验证其实际输出风格和适配程度。
3. 两者均可作为后续模型运行阶段的候补方案。

适合的 ZDoc 场景：

1. `qwen3:14b`：中等资源下的通用文本生成、结构化说明、短章节草稿。
2. `deepseek-r1:32b`：复杂规则分析、边界检查、推理链路草稿。

限制：

1. 本节点不进行推理质量判断。
2. 本节点不输入 prompt。
3. 后续运行任一备选模型仍需单独授权。

## 17. ZDoc 场景匹配矩阵

| ZDoc 场景 | 建议候选 | 说明 |
| --- | --- | --- |
| 默认通用文档生成 | `qwen3:30b` | 作为后续受控运行的默认质量基线候选。 |
| 编码 / 工程辅助 | `qwen3-coder:30b` | 用于配置、代码、命令和错误信息解释类任务。 |
| 高质量长文档候选 | `qwen3-next:80b-a3b-instruct-q8_0` | 资源风险最高，适合后续明确边界后再验证。 |
| 高质量次优先候选 | `qwen3.6:35b` | 适合作为 80b 之外的高规格候选。 |
| 轻量快速验证 | `qwen3:0.6b` | 适合未来最小调用链 smoke test。 |
| 快速交互候选 | `qwen3:8b` | 适合低资源短文本模拟任务。 |
| 中等资源备选 | `qwen3:14b` | 作为默认模型的资源更低备选。 |
| 复杂分析备选 | `deepseek-r1:32b` | 适合后续推理类模拟验证候选。 |

## 18. 模型选择判定

判定：`PASS`。

判定依据：

1. 仓库路径正确。
2. 分支为 `main`。
3. HEAD/tag 与 039 基线一致。
4. 工作区 clean。
5. 037 Ollama model inventory `PASS` 已复核。
6. 038 inventory result closed 已复核。
7. 039 model selection authorization boundary 已复核。
8. 038 已记录 8 个本地模型名称。
9. 本节点可在不执行任何 Ollama 命令、不运行模型、不输入 prompt、不读取真实数据的前提下形成静态模型选择建议。
10. 本节点未触发任何阻断条件。

## 19. 后续模型运行授权要求

本节点明确：

1. 本节点 PASS 不等于授权模型运行。
2. 本节点 PASS 不等于授权 `ollama run`。
3. 本节点 PASS 不等于授权 prompt 输入。
4. 本节点 PASS 不等于授权模型推理。
5. 本节点 PASS 不等于授权读取真实 KG / 真实项目资料。
6. 本节点 PASS 不等于授权 trial。
7. 本节点 PASS 不等于授权 generation/export/write-back。

后续如需运行模型，必须另设：

`LOCAL-LAUNCHER-041-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-SELECTION-RESULT-RECORD-GATE`

之后再由新的模型运行授权门决定是否可进入模型运行，不得从本节点直接运行模型。

## 20. 实际执行命令清单

LOCAL-LAUNCHER-040 仅执行 Git 状态确认和指定文档只读查看：

```bash
pwd
git status --short
git branch --show-current
git rev-parse HEAD
git tag --points-at HEAD
git log -1 --oneline
git diff --check
git diff --cached --check
sed -n '1,260p' docs/zdoc-local-launcher-v1-ollama-model-selection-authorization-gate-local-launcher-039.md
sed -n '1,260p' docs/zdoc-local-launcher-v1-ollama-model-inventory-result-record-gate-local-launcher-038.md
sed -n '1,260p' docs/zdoc-local-launcher-v1-ollama-model-inventory-execution-gate-local-launcher-037.md
sed -n '1,260p' docs/zdoc-local-launcher-v1-ollama-model-inventory-authorization-gate-local-launcher-036.md
sed -n '261,520p' docs/zdoc-local-launcher-v1-ollama-model-selection-authorization-gate-local-launcher-039.md
sed -n '261,520p' docs/zdoc-local-launcher-v1-ollama-model-inventory-execution-gate-local-launcher-037.md
sed -n '261,520p' docs/zdoc-local-launcher-v1-ollama-model-inventory-authorization-gate-local-launcher-036.md
```

未执行任何 Ollama 命令、模型命令、服务命令、endpoint 请求、HTTP request、安装命令、测试、lint、build、真实数据读取、日志正文读取、trial、generation、export 或 write-back。

## 21. 禁止项确认

本节点确认：

1. 未修改 V1 页面产物。
2. 未修改 V0。
3. 未修改 backend/frontend/config/dependency。
4. 未新增 JS 文件。
5. 未创建脚本。
6. 未创建真正 App 包。
7. 未运行 npm/yarn/pnpm/pip。
8. 未运行测试/lint/build。
9. 未打开 HTML 页面。
10. 未启动新 ZDoc 服务。
11. 未重启 ZDoc 服务。
12. 未停止 ZDoc 服务。
13. 未启动新的 Ollama server。
14. 未重启 Ollama server。
15. 未停止 Ollama server。
16. 未访问 endpoint。
17. 未执行 curl / HTTP request。
18. 未再次访问 `/health`。
19. 未执行 `ollama list`。
20. 未执行 `ollama run`。
21. 未执行 `ollama pull`。
22. 未执行 `ollama serve`。
23. 未执行任何 Ollama 模型命令。
24. 未执行模型推理。
25. 未输入 prompt。
26. 未下载/删除/创建模型。
27. 未读取真实 KG。
28. 未读取真实项目资料。
29. 未读取真实招标文件。
30. 未读取 `.env` / secrets / tokens / credentials。
31. 未读取 registration / metadata / proof / manifest / sample 实例。
32. 未读取 output/job/export 正文。
33. 未读取日志正文。
34. 未触发 generation/export/write-back。
35. 未写 output/job/export。
36. 未进入 trial。
37. 未进入真实使用。
38. 未进入 50 人正式使用。
39. 未进入 `LOCAL-LAUNCHER-041`。

## 22. 当前 Decision

`LOCAL-LAUNCHER-040 ZDOC LOCAL APP V1 OLLAMA MODEL SELECTION EXECUTION GATE PASSED / MODEL SELECTION RECOMMENDATION COMPLETED BASED ON RECORDED LOCAL INVENTORY / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`

## 23. 下一节点建议

若 ChatGPT 总控师审核通过，下一节点建议为：

`LOCAL-LAUNCHER-041-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-SELECTION-RESULT-RECORD-GATE`

041 只能记录 040 模型选择结果，不得运行模型，不得输入 prompt，不得读取真实 KG / 真实项目资料，不得触发 generation/export/write-back。

## 24. 明确说明未进入 `LOCAL-LAUNCHER-041`

本节点未进入 `LOCAL-LAUNCHER-041`。
