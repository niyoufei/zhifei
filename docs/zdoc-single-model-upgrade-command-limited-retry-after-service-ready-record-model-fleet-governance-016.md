# MODEL-FLEET-GOVERNANCE-016: Single-Model Upgrade Command-Limited Retry After Service Ready Record

## 1. Baseline

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Starting HEAD: `8400e49bed00d0beac59a79c52007afd9ec0d6ad`
- Starting tag at HEAD: not queried because this node's allowed command list did not include a tag lookup command.
- Starting `git status --short`: clean
- Previous node: `MODEL-FLEET-GOVERNANCE-015`
- Previous decision:

  `OLLAMA SERVICE-STATE HANDLING GATE FORMED / PATH A RECOMMENDED / NO OLLAMA EXECUTION IN THIS NODE`

This node is a service-ready command-limited single-model retry execution record.

This node was executed under "完全访问权限".

This node does not authorize stability validation, ZDoc service execution, endpoint access, real KG reading or parsing, generation / export / write-back, output / job / export writes, image generation, real use, or trial.

## 2. Inputs Reviewed

The following prescribed prior docs files were read:

1. `docs/zdoc-ollama-service-state-handling-authorization-gate-model-fleet-governance-015.md`
2. `docs/zdoc-single-model-upgrade-retry-failure-audit-model-fleet-governance-014.md`
3. `docs/zdoc-single-model-upgrade-command-limited-full-access-retry-record-model-fleet-governance-013.md`
4. `docs/zdoc-single-model-upgrade-blocked-audit-model-fleet-governance-012.md`
5. `docs/zdoc-single-model-upgrade-command-limited-execution-record-model-fleet-governance-011.md`
6. `docs/zdoc-single-model-upgrade-execution-authorization-model-fleet-governance-010.md`

No real KG file body content was read.

No real KG JSON was parsed.

## 3. Service-Ready Evidence

The user manually started Ollama before this node.

The user's local `ollama list` had already returned successfully before this node.

The user-provided screenshot evidence showed that `qwen3:30b` already existed locally.

The user-provided screenshot showed the following `qwen3:30b` information:

- ID: `ad815644918f`
- SIZE: `18 GB`
- MODIFIED: `5 weeks ago`

This information is treated as user-provided service-ready evidence.

Codex still executed the pull-before `ollama list` inside this node and recorded the actual result below.

## 4. Authorized Model

- Unique authorized model for this node: `qwen3:30b`
- Associated candidate: `Qwen/Qwen3-30B-A3B-Instruct-2507`
- Scope: this node must not expand to any other model.

No other model was authorized for pull, upgrade, deletion, replacement, validation, real use, or trial.

## 5. Pre-Execution Checks

- Starting `git status --short`: clean
- Starting HEAD: `8400e49bed00d0beac59a79c52007afd9ec0d6ad`
- Disk-space quick check:

```text
Filesystem      Size    Used   Avail Capacity iused ifree %iused  Mounted on
/dev/disk3s5   3.6Ti   673Gi   3.0Ti    19%    2.6M   32G    0%   /System/Volumes/Data
```

- Disk-space judgment: not obviously insufficient for the authorized command-limited node.
- Pull-before command executed:

```bash
ollama list
```

- Pull-before `ollama list` result: success.
- Pull-before model inventory summary:

```text
NAME                                ID              SIZE      MODIFIED
qwen3.6:35b                         07d35212591f    23 GB     23 hours ago
qwen3-next:80b-a3b-instruct-q8_0    fc9e251d7f37    84 GB     5 weeks ago
qwen3-coder:30b                     06c1097efce0    18 GB     5 weeks ago
deepseek-r1:32b                     edba8017331d    19 GB     5 weeks ago
qwen3:30b                           ad815644918f    18 GB     5 weeks ago
qwen3:14b                           bdbd181c33f2    9.3 GB    5 weeks ago
qwen3:8b                            500a1f067a9f    5.2 GB    5 weeks ago
qwen3:0.6b                          7df6b6e09427    522 MB    5 weeks ago
```

Pull-before `qwen3:30b` existed.

Pull-before `qwen3:30b` ID / SIZE / MODIFIED:

```text
ID: ad815644918f
SIZE: 18 GB
MODIFIED: 5 weeks ago
```

## 6. Pull Execution

Actual command executed:

```bash
ollama pull qwen3:30b
```

Execution result: success.

Recorded output summary:

```text
pulling manifest
pulling 58574f2e94b9: 100% 18 GB
pulling 2d54db2b9bb2: 100% 1.5 KB
pulling d18a5cc71b84: 100% 11 KB
pulling cff3f395ef37: 100% 120 B
pulling 3cdc64c2b371: 100% 494 B
verifying sha256 digest
writing manifest
success
```

No retry was performed.

No alternate model was pulled.

No model name was changed.

## 7. Post-Execution Inventory

Pull-after command executed:

```bash
ollama list
```

Pull-after `ollama list` result: success.

Pull-after model inventory summary:

```text
NAME                                ID              SIZE      MODIFIED
qwen3:30b                           ad815644918f    18 GB     8 seconds ago
qwen3.6:35b                         07d35212591f    23 GB     23 hours ago
qwen3-next:80b-a3b-instruct-q8_0    fc9e251d7f37    84 GB     5 weeks ago
qwen3-coder:30b                     06c1097efce0    18 GB     5 weeks ago
deepseek-r1:32b                     edba8017331d    19 GB     5 weeks ago
qwen3:14b                           bdbd181c33f2    9.3 GB    5 weeks ago
qwen3:8b                            500a1f067a9f    5.2 GB    5 weeks ago
qwen3:0.6b                          7df6b6e09427    522 MB    5 weeks ago
```

Pull-after `qwen3:30b` existed.

Pull-after `qwen3:30b` ID / SIZE / MODIFIED:

```text
ID: ad815644918f
SIZE: 18 GB
MODIFIED: 8 seconds ago
```

Other existing models were retained.

Other existing models were not deleted by this node.

Other existing models were not replaced by this node.

No `latest` pointer was modified by this node.

## 8. Boundary Confirmation

- 未执行 `ollama run`
- 未执行 `ollama rm`
- 未执行 `ollama serve`
- 未执行除授权命令外的其他 Ollama 命令
- 未升级、拉取、删除或替换其他模型
- 未删除其他模型
- 未替换其他模型
- 未修改 latest 指向
- 未运行 ZDoc 服务
- 未访问 endpoint
- 未读取真实 KG
- 未解析 KG JSON
- 未触发 generation / export / write-back
- 未写 output / job / export
- 未生成图片
- 未调用图像生成工具或图像模型
- 未进入真实使用或试用

Additional boundary confirmations:

- No model other than `qwen3:30b` was pulled or upgraded.
- No multi-model upgrade was performed.
- No stability validation was entered.
- No KG safety access was entered.
- No ZDoc preview / trial / production path was entered.
- No online model-version lookup was performed.

## 9. Current Decision

`SERVICE-READY COMMAND-LIMITED SINGLE-MODEL PULL COMPLETED / STABILITY VALIDATION NOT AUTHORIZED`

This decision is based on successful pull-before inventory, successful `ollama pull qwen3:30b`, and successful pull-after inventory.

This decision does not authorize stability validation in this node.

This decision does not authorize ZDoc service execution in this node.

This decision does not authorize real KG access, real use, or trial.

## 10. NO-GO Statements

`NO-GO FOR OLLAMA RUN`

`NO-GO FOR OLLAMA RM`

`NO-GO FOR OLLAMA SERVE`

`NO-GO FOR MULTI-MODEL UPGRADE`

`NO-GO FOR IMAGE GENERATION EXECUTION`

`NO-GO FOR REAL USE`

`NO-GO FOR TRIAL`

`NO-GO FOR ZDOC SERVICE EXECUTION`

`NO-GO FOR KG READ / PARSE`

`NO-GO FOR GENERATION / EXPORT / WRITE-BACK`

## 11. Next Recommended Node

Because the service-ready command-limited pull completed successfully, the recommended next node is:

`MODEL-FLEET-GOVERNANCE-017-SINGLE-MODEL-STABILITY-AUTHORIZATION-GATE`

The next node must not execute automatically.

The next node must wait for ChatGPT controller review of this report before any further decision.

The next node must not automatically enter ZDoc service execution, KG safety access, real use, trial, or ZDoc preview / trial / production flow.

MODEL-FLEET-GOVERNANCE-016 stops here and waits for human review.
