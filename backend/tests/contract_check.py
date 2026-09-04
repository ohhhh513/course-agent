"""契约测试：验证后端返回形状 = 前端契约。

运行：cd backend && python tests/contract_check.py
依赖：pip install fastapi uvicorn httpx

它用 FastAPI TestClient 真实调用接口，断言：
  - 受保护接口未带 token -> 401
  - 带 token 后 -> 信封 code==0 且含 data
  - 关键 GET 的 data 顶层键与前端 mock_data.json 一致（形状对齐闸门）
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.data.seed import reset_db  # noqa: E402

reset_db()

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

SEED_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "data", "mock_data.json")
with open(SEED_PATH, encoding="utf-8") as f:
    SEED = json.load(f)

client = TestClient(app)
failures = []


def check(cond, msg):
    if cond:
        print("  PASS", msg)
    else:
        print("  FAIL", msg)
        failures.append(msg)


print("== 未鉴权应 401 ==")
r = client.get("/api/v1/student/dashboard")
check(r.status_code == 401, f"GET /student/dashboard 无 token -> 401 (got {r.status_code})")

print("== 登录 ==")
r = client.post("/api/v1/auth/login", json={"username": "student", "password": "123456", "role": "student"})
check(r.status_code == 200 and r.json()["code"] == 0, "学生登录成功")
token = r.json()["data"]["token"]
check(bool(token), "返回 JWT token")
hdr = {"Authorization": f"Bearer {token}"}

print("== 受保护 GET 信封 + data 存在 ==")
endpoints = [
    "/student/dashboard", "/student/mastery/matrix", "/student/ability/radar",
    "/student/growth", "/student/compare", "/student/alerts", "/student/messages",
    "/graph?type=knowledge", "/graph?type=problem", "/graph?type=goal", "/graph/path",
    "/graph/kp/KP01", "/ai/methods", "/ai/sessions", "/ai/suggest-questions",
    "/practice/modes", "/practice/wrong-book",
    "/teacher/dashboard", "/teacher/heatmap", "/teacher/students",
    "/teacher/students/S20260317/profile", "/teacher/alerts",
    "/analysis/errors", "/analysis/weak-chain", "/analysis/causes",
    "/question/gen/config", "/question/bank",
    "/intervention/list", "/intervention/templates",
    "/report/list", "/course/C2026DS001",
]
for ep in endpoints:
    r = client.get("/api/v1" + ep, headers=hdr)
    j = r.json()
    check(r.status_code == 200 and j.get("code") == 0 and "data" in j,
          f"GET {ep} -> code==0 且含 data (got {r.status_code}/{j.get('code')})")

print("== 关键端点 data 形状对齐 mock_data.json ==")
checks_shape = [
    ("/student/dashboard", "studentDashboard"),
    ("/graph?type=knowledge", "knowledgeGraph"),
    ("/teacher/dashboard", "teacherDashboard"),
    ("/analysis/errors", "errorAnalysis"),
    ("/question/gen/config", "genConfig"),
]
for ep, key in checks_shape:
    r = client.get("/api/v1" + ep, headers=hdr)
    got = set((r.json().get("data") or {}).keys())
    want = set((SEED.get(key) or {}).keys())
    # 允许后端返回字段多于 mock（扩字段无害），但不应少于
    check(want.issubset(got), f"{ep} data 顶层键 ⊇ mock.{key} (缺: {want - got})")

print("== POST 最小逻辑 ==")
r = client.post("/api/v1/practice/answers", headers=hdr, json={"qId": "Q1024", "answer": "B"})
check(r.json().get("code") == 0 and "correct" in r.json()["data"], "练习判分返回 correct 字段")
r = client.post("/api/v1/ai/chat", headers=hdr, json={"question": "Dijkstra 为什么不能处理负权边？", "method": "guided"})
check(r.status_code == 200 and r.json().get("code") == 0 and r.json()["data"].get("available") is False,
      "AI 答疑暂缓上线 -> available=False 且明确提示（后期接入）")

print()
if failures:
    print(f"结果：{len(failures)} 项失败")
    for f in failures:
        print("  -", f)
    sys.exit(1)
else:
    print("结果：全部通过 ✅")
