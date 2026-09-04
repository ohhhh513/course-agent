"""深度契约体检：后端返回形状 vs 前端 mock_data.json（逐层字段 + 类型）。

为什么需要它
------------
`contract_check.py` 只比对 data 的**顶层键**，会漏掉绝大多数真实对接问题：
前端渲染用的是 `d.overview.currentStreak`、`s.mastery`、`p.metrics.rank` 这类
**深层字段**。只要深层字段名或类型对不上，页面就会出现 undefined、图表空白、
排序失效等问题——而这些在顶层键检查里全是绿的。

本脚本逐层比对（对象键、数组元素结构、标量类型），把差异一次性量化出来，
作为后端开发的**主闸门**。

运行：cd backend && python tests/shape_diff.py
      加 --verbose 打印后端多出的字段（扩展字段无害，默认只报缺失/类型不符）
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "app", "data", "mock_data.json"), encoding="utf-8") as f:
    MOCK = json.load(f)

client = TestClient(app)
VERBOSE = "--verbose" in sys.argv


def _t(v):
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, (int, float)):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "array"
    if isinstance(v, dict):
        return "object"
    return "null"


def diff(exp, got, path="$", out=None, depth=0):
    """逐层比对，收集差异（只关心前端消费得到的字段：以 mock 为准）。"""
    if out is None:
        out = []
    if depth > 8:
        return out
    et, gt = _t(exp), _t(got)
    if et == "null":
        return out  # mock 里的 null 不做约束
    if et != gt:
        out.append(f"{path}: 类型不符 mock={et} 后端={gt}")
        return out
    if et == "object":
        for k, v in exp.items():
            if k not in got:
                out.append(f"{path}.{k}: 后端缺失")
            else:
                diff(v, got[k], f"{path}.{k}", out, depth + 1)
        if VERBOSE:
            for k in got:
                if k not in exp:
                    out.append(f"{path}.{k}: [扩展字段] 后端多出")
    elif et == "array" and exp:
        if not got:
            out.append(f"{path}: 后端返回空数组（mock 有 {len(exp)} 项）")
        else:
            diff(exp[0], got[0], f"{path}[0]", out, depth + 1)
    return out


def unwrap_list(data):
    """后端分页统一包 {total, list:[...]}，比对时取 list。"""
    if isinstance(data, dict) and "list" in data:
        return data["list"]
    return data


def pick(exp, mode):
    """处理「mock 以 id 为键、后端直接返回对象」的详情类端点。

    例：mock.kpDetail = {"KP52": {...}}，而 GET /graph/kp/KP52 直接返回 {...}。
    这时要解包的是 **mock** 而不是后端响应——之前解错了方向，
    导致误报「$: 类型不符 mock=object 后端=string」。
    """
    if not isinstance(exp, dict) or not mode:
        return exp
    if mode == "first":
        return list(exp.values())[0] if exp else exp
    if mode.startswith("pick:"):
        key = mode.split(":", 1)[1]
        return exp.get(key, list(exp.values())[0] if exp else exp)
    return exp


# (方法, 路径, mock 键, 角色, 解包方式)
#   解包方式：None        —— 后端与 mock 直接逐层比对
#             "list"      —— 双方都取 data["list"]（分页包）
#             "pick:<id>" —— mock 是以 id 为键的字典，按 id 取出后再比对（详情类端点）
CASES = [
    ("GET", "/student/dashboard", "studentDashboard", "student", None),
    ("GET", "/student/mastery/matrix", "masteryMatrix", "student", None),
    ("GET", "/student/ability/radar", "abilityRadar", "student", None),
    ("GET", "/student/growth", "growthTrack", "student", None),
    ("GET", "/student/compare", "classCompare", "student", None),
    ("GET", "/student/alerts", "studentAlerts", "student", "list"),
    ("GET", "/student/messages", "messages", "student", "list"),
    ("GET", "/student/resources", "resources", "student", "list"),
    ("GET", "/graph?type=knowledge", "knowledgeGraph", "student", None),
    ("GET", "/graph?type=problem", "problemGraph", "student", None),
    ("GET", "/graph?type=goal", "goalGraph", "student", None),
    ("GET", "/graph/path", "learningPath", "student", None),
    ("GET", "/graph/kp/KP52", "kpDetail", "student", "pick:KP52"),
    ("GET", "/ai/methods", "teachingMethods", "student", None),
    ("GET", "/ai/sessions", "chatHistory", "student", "list"),
    ("GET", "/practice/modes", "practiceModes", "student", None),
    ("GET", "/practice/wrong-book", "wrongBook", "student", "list"),
    ("GET", "/practice/wrong-book/Q0912/detail", "wrongDetail", "student", "pick:Q0912"),
    ("GET", "/course/C2026DS001", "course", "student", None),
    ("GET", "/teacher/dashboard", "teacherDashboard", "teacher", None),
    ("GET", "/teacher/heatmap?classId=CL2301", "heatmap", "teacher", None),
    ("GET", "/teacher/students?classId=CL2301", "students", "teacher", "list"),
    ("GET", "/teacher/students/S20260317/profile", "studentProfile", "teacher", None),
    ("GET", "/teacher/alerts?classId=CL2301", "teacherAlerts", "teacher", "list"),
    ("GET", "/analysis/errors", "errorAnalysis", "teacher", None),
    ("GET", "/question/gen/config", "genConfig", "teacher", None),
    ("GET", "/question/bank", "questionBank", "teacher", "list"),
    ("GET", "/intervention/list", "interventions", "teacher", "list"),
    ("GET", "/intervention/templates", "strategyTemplates", "teacher", None),
    ("GET", "/intervention/IV1/effect", "interventionEffect", "teacher", None),
    ("GET", "/report/list", "reportList", "teacher", "list"),
    ("GET", "/report/RP2026082801", "reportDetail", "teacher", None),
]


def login(role):
    r = client.post("/api/v1/auth/login", json={"username": role, "password": "123456", "role": role})
    return r.json()["data"]["token"]


def main():
    tokens = {r: {"Authorization": f"Bearer {login(r)}"} for r in ("student", "teacher")}
    total_diff = 0
    bad_cases = []

    for method, path, key, role, mode in CASES:
        r = client.request(method, "/api/v1" + path, headers=tokens[role])
        label = f"{method} {path}  ↔  mock.{key}"
        if r.status_code != 200 or r.json().get("code") != 0:
            print(f"FAIL {label} — HTTP {r.status_code} / code={r.json().get('code')}")
            bad_cases.append(label)
            total_diff += 1
            continue
        exp = pick(MOCK.get(key), mode)
        got = r.json().get("data")
        if mode == "list":
            exp, got = unwrap_list(exp), unwrap_list(got)
        d = diff(exp, got)
        if d:
            print(f"FAIL {label}  （{len(d)} 处差异）")
            for line in d[:25]:
                print("      " + line)
            if len(d) > 25:
                print(f"      ... 另有 {len(d) - 25} 处")
            bad_cases.append(label)
            total_diff += len(d)
        else:
            print(f"PASS {label}")

    print()
    if bad_cases:
        print(f"结果：{len(bad_cases)}/{len(CASES)} 个端点形状不一致，共 {total_diff} 处差异")
        sys.exit(1)
    print(f"结果：全部通过 ✅  {len(CASES)} 个端点逐层形状对齐 mock_data.json")


if __name__ == "__main__":
    main()
