# Backend Runbook (macOS)

## 1) 重启后快速启动（必做）
### Terminal 1：启动 API 服务（保持窗口不退出）
    cd "$HOME/Desktop/文档生成系统/backend"
    python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

### Terminal 2：运行全量 Smoke 测试（跑完会自动退出）
    cd "$HOME/Desktop/文档生成系统/backend"
    ./scripts/run_smoke.sh

## 2) 8000 端口被占用时才需要做（可选）
    lsof -nP -iTCP:8000 -sTCP:LISTEN
    # 找到 PID 后执行（把 PID 换成数字）：
    kill -9 PID

## 3) 常用自检（可选）
    curl -s http://127.0.0.1:8000/openapi.json | head -n 5
    curl -s http://127.0.0.1:8000/audit | python3 -m json.tool | head -n 60
