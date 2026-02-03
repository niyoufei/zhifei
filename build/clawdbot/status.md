# clawdbot status
- last_run: 2026-02-03T初始化
- last_result: blocked
- last_action: 检查 goal.md，发现为空模板
- next_step: 等待用户在 goal.md 中定义任务

## 本轮动作
- 读取 goal.md、status.md、blockers.md
- 发现 goal.md 是空模板，无具体任务定义
- 记录阻塞到 blockers.md

## 证据
```
goal.md 内容:
# clawdbot 目标（把你真实任务粘贴到这里）
- 系统最终目标：（空）
- 当前卡点：（空）
- DoD：（空）
```

## 下一步
用户需填写 goal.md 后重新触发 clawdbot
