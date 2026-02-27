#!/usr/bin/env python3
"""
快速接口冒烟：只检查 /health、/capabilities、/config 是否可用（无需登录）。
用法：先启动服务，再运行
  python3 scripts/smoke_api.py
  python3 scripts/smoke_api.py http://127.0.0.1:8010
"""
import sys
import urllib.request
import urllib.error

def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010"
    base = base.rstrip("/")
    ok = True
    for path in ["/health", "/capabilities", "/config"]:
        url = base + path
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as r:
                if r.status != 200:
                    print(f"[FAIL] {path} status={r.status}")
                    ok = False
                else:
                    print(f"[OK]   {path}")
        except urllib.error.HTTPError as e:
            print(f"[FAIL] {path} HTTP {e.code}")
            ok = False
        except Exception as e:
            print(f"[FAIL] {path} {e}")
            ok = False
    if ok:
        print("Smoke API: PASS")
        return 0
    print("Smoke API: FAIL")
    return 1

if __name__ == "__main__":
    sys.exit(main())
