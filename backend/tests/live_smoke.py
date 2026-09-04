"""实时 HTTP 冒烟脚本：对真实运行的 uvicorn 服务做端到端 HTTP 校验。

覆盖范围（契约测试 tests/contract_check.py 未覆盖的端点）：
  - /health、登录、/auth/profile、/auth/reset-password（含还原演示密码）
  - 练习闭环：组卷 -> 提交判分 -> 结束生成报告
  - /question/bank + /question/review
  - /intervention/list + /intervention/{iv}/confirm
  - /ai/chat（断言 available=False）、/ai/feedback
  - /graph/kp/{kpId}、/teacher/heatmap
  - 未鉴权 401

用法：
  1) 先启动服务： python -m uvicorn app.main:app --host 127.0.0.1 --port 8011
  2) 再跑本脚本：   python tests/live_smoke.py
可选环境变量 BASE_URL 覆盖地址（默认 http://127.0.0.1:8011）。
"""
import json
import os
import sys
import urllib.request
import urllib.error

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.environ.get("BASE_URL", "http://127.0.0.1:8011")


def req(method, path, body=None, token=None, root=False):
    url = (ROOT if root else ROOT + "/api/v1") + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


fails = []
def check(name, cond, extra=""):
    print(("PASS" if cond else "FAIL"), name, extra)
    if not cond:
        fails.append(name)


# 1. health
s, j = req("GET", "/health", root=True)
check("GET /health -> 200", s == 200, str(s))

# 2. 登录（学生 + 教师）
s, j = req("POST", "/auth/login", {"username": "student", "password": "123456", "role": "student"})
check("登录(学生) code0+token", s == 200 and j.get("code") == 0 and bool(j["data"].get("token")))
stu = j["data"]["token"]
s, j = req("POST", "/auth/login", {"username": "teacher", "password": "123456", "role": "teacher"})
tea = j["data"]["token"]
check("登录(教师) code0", s == 200 and j.get("code") == 0)

# 3. profile + reset-password（契约未覆盖）
s, j = req("GET", "/auth/profile", token=stu)
check("GET /auth/profile code0", j.get("code") == 0)
s, j = req("POST", "/auth/reset-password", {"username": "student", "password": "654321"})
check("POST /auth/reset-password code0", j.get("code") == 0 and j["data"].get("ok") is True)
# 还原，避免破坏演示账号
req("POST", "/auth/reset-password", {"username": "student", "password": "123456"})

# 4. 学生驾驶舱（快照）
s, j = req("GET", "/student/dashboard", token=stu)
check("GET /student/dashboard code0", j.get("code") == 0)

# 5. 练习闭环（真实）
s, j = req("POST", "/practice/sessions", {"mode": "random", "count": 2}, token=stu)
check("POST /practice/sessions code0+questions", j.get("code") == 0 and isinstance(j["data"].get("questions"), list))
sid = j["data"]["sessionId"]
q0 = j["data"]["questions"][0]["qId"] if j["data"]["questions"] else None
if q0:
    s, j = req("POST", "/practice/answers", {"sessionId": "cur", "qId": q0, "answer": "A"}, token=stu)
    check("POST /practice/answers code0+correct字段", j.get("code") == 0 and "correct" in j["data"])
s, j = req("POST", f"/practice/sessions/{sid}/finish", token=stu)
check("POST /practice/sessions/finish code0+accuracy", j.get("code") == 0 and "accuracy" in j["data"])

# 6. 题库 + 审核（契约未覆盖 review）
s, j = req("GET", "/question/bank", token=tea)
check("GET /question/bank code0+list", j.get("code") == 0 and isinstance(j["data"].get("list"), list))
bank_q = j["data"]["list"][0]["qId"] if j["data"].get("list") else None
if bank_q:
    s, j = req("POST", "/question/review", {"qIds": [bank_q], "action": "publish"}, token=tea)
    check("POST /question/review code0+affected", j.get("code") == 0 and j["data"].get("affected") == 1)

# 7. 干预（契约未覆盖 confirm）
s, j = req("GET", "/intervention/list", token=tea)
check("GET /intervention/list code0", j.get("code") == 0)
iv = j["data"]["list"][0]["ivId"] if j["data"].get("list") else None
if iv:
    s, j = req("POST", f"/intervention/{iv}/confirm", {"steps": [{"title": "订正练习"}]}, token=tea)
    check("POST /intervention/confirm code0+ok", j.get("code") == 0 and j["data"].get("ok") is True)

# 8. AI（暂缓态）
s, j = req("POST", "/ai/chat", {"question": "Dijkstra 为什么不能处理负权边？", "method": "guided"}, token=stu)
check("POST /ai/chat available=False", j.get("code") == 0 and j["data"].get("available") is False)
s, j = req("POST", "/ai/feedback", {"accepted": True}, token=stu)
check("POST /ai/feedback code0", j.get("code") == 0)

# 9. 知识点详情（真实）
s, j = req("GET", "/graph/kp/KP52", token=stu)
check("GET /graph/kp/KP52 code0+name", j.get("code") == 0 and j["data"].get("name"))

# 10. 教师热力图（真实）
s, j = req("GET", "/teacher/heatmap", token=tea)
check("GET /teacher/heatmap code0+data", j.get("code") == 0 and "data" in j)

# 11. 未鉴权 401
s, j = req("GET", "/student/dashboard")
check("未鉴权 -> 401", s == 401, str(s))

print()
if fails:
    print("结果：%d 项失败 ->" % len(fails), fails)
    raise SystemExit(1)
else:
    print("结果：全部通过 ✅（live HTTP 冒烟）")
