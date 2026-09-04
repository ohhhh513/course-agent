"""数据种子层：把前端契约数据（mock_data.json）落成真实关系表。

职责边界
--------
- **本模块只负责「首次建库 + 灌种子」**，不参与任何业务查询；业务一律走 `repo` / `services`。
- 每张表独立幂等（表非空则跳过），因此在已有库上重复启动不会覆盖用户的真实数据。
- 种子数据来自 `mock_data.json`（前端契约单一真相源），保证后端字段语义与前端一致。

字段映射原则
------------
mock 里的字段名就是前端消费的字段名。种子层负责把 mock 的**展示型字段**
（如学生姓名轴、知识点简称轴）解析成真实的 **ID 外键**：
  - heatmap.kpAxis 是知识点简称（"Dijkstra"）→ 解析为 kpId（KP52）
  - heatmap.studentAxis 是学生姓名（"陈思远"）→ 解析为 userId（S20260317）
这样真实表之间才能 JOIN，查询服务也才能按 ID 聚合。

历史作答（submissions）由掌握度反推合成（确定性伪随机，同一份种子结果稳定），
使「错题本 / 掌握矩阵 / 学情分析 / 驾驶舱」一开始就有真实可查的数据，
而不是等用户做完几套练习才有东西看。
"""
import json
import os
import random
import traceback
from datetime import datetime, timedelta, timezone

from ..core.security import DEMO_USERS
from ..db import models as _m  # noqa: F401  确保模型注册到 Base.metadata
from ..db.base import Base
from ..db.session import SessionLocal, engine

_HERE = os.path.dirname(os.path.abspath(__file__))
_MOCK_PATH = os.path.join(_HERE, "mock_data.json")

_DEMO_STUDENT = "S20260317"
_DEFAULT_CLASS = "CL2301"
_COURSE_ID = "C2026DS001"
_PREFIX = "/api/v1"

# 目标图谱节点 → 关联知识点（用于按真实掌握率计算达成度）
_GOAL_KP = {
    "G1": ["KP11", "KP12", "KP13", "KP14"],
    "G2": ["KP31", "KP32", "KP33", "KP34", "KP44"],
    "G3": ["KP41", "KP42", "KP43", "KP51", "KP52", "KP53"],
    "G4": ["KP01", "KP02"],
    "G1-1": ["KP12", "KP13", "KP14"],
    "G1-2": ["KP21", "KP22", "KP23", "KP24"],
    "G2-1": ["KP31", "KP32", "KP33"],
    "G2-2": ["KP44"],
    "G2-3": ["KP34"],
    "G3-1": ["KP41", "KP42"],
    "G3-2": ["KP43"],
    "G3-3": ["KP51", "KP52", "KP53"],
    "G4-1": ["KP01", "KP02"],
}

# 问题图谱节点 → 关联知识点（用于按真实作答计算错误率）
_PROBLEM_KP = {
    "PB1": ["KP41", "KP42", "KP43", "KP51", "KP52", "KP53"],
    "PB1-1": ["KP41"], "PB1-2": ["KP42"], "PB1-3": ["KP52"],
    "PB2": ["KP21", "KP22", "KP23", "KP24"], "PB2-1": ["KP24"], "PB2-2": ["KP21"],
    "PB3": ["KP44"], "PB3-1": ["KP44"],
}

_seeded = False


# ---------------------------------------------------------------- 基础工具

def _load_mock() -> dict:
    if not os.path.exists(_MOCK_PATH):
        return {}
    with open(_MOCK_PATH, encoding="utf-8") as f:
        return json.load(f)


def _to_int(v, default=0) -> int:
    try:
        return int(v)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return default


def _to_float(v, default=0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def _norm_ts(v: str) -> str:
    """把 mock 里各种时间写法统一成 'YYYY-MM-DD HH:MM'。"""
    if not v:
        return _now()
    v = str(v).strip()
    if len(v) == 11 and v[2] == "-":          # "08-27 20:15"
        return "2026-" + v
    return v


def _safe(fn, name=""):
    """单表播种失败不应拖垮整库（记录后继续）。"""
    try:
        fn()
    except Exception:
        print(f"[seed] 播种 {name or fn.__name__} 失败：")
        traceback.print_exc()


# ---------------------------------------------------------------- 名称 → ID

# heatmap 的知识点简称 → 真实 kpId（简称与全称无法纯字符串匹配时的兜底）
_KP_ALIAS = {
    "算法复杂度": "KP01", "顺序表": "KP12", "单链表": "KP13", "栈": "KP21",
    "队列": "KP22", "循环队列": "KP23", "二叉树概念": "KP31", "二叉树遍历": "KP32",
    "哈夫曼树": "KP44", "图的存储": "KP42", "DFS/BFS": "KP43",
    "最小生成树": "KP51", "Dijkstra": "KP52",
}


def _build_kp_resolver(kps: list):
    """返回 name -> kpId 的解析函数（先精确、再别名、最后包含匹配）。"""
    exact = {kp.name: kp.kpId for kp in kps}
    norm = {kp.name.replace(" ", "").replace("/", ""): kp.kpId for kp in kps}

    def resolve(name: str) -> str:
        if not name:
            return ""
        if name in exact:
            return exact[name]
        if name in _KP_ALIAS:
            return _KP_ALIAS[name]
        key = name.replace(" ", "").replace("/", "")
        if key in norm:
            return norm[key]
        for kp in kps:
            k = kp.name.replace(" ", "").replace("/", "")
            if key and (key in k or k in key):
                return kp.kpId
        return ""
    return resolve


# ---------------------------------------------------------------- 入口

def ensure_db() -> None:
    """幂等：建表 + 空表灌种子。可安全重复调用。"""
    global _seeded
    Base.metadata.create_all(bind=engine)
    if _seeded:
        return
    data = _load_mock()
    with SessionLocal() as s:
        _safe(lambda: _seed_users(s), "users")
        _safe(lambda: _seed_classes(s, data), "classes")
        _safe(lambda: _seed_courses(s, data), "courses")
        _safe(lambda: _seed_knowledge_points(s, data), "knowledge_points")
        _safe(lambda: _seed_questions(s, data), "questions")
        _safe(lambda: _seed_resources(s, data), "resources")
        _safe(lambda: _seed_messages(s, data), "messages")
        _safe(lambda: _seed_students(s, data), "students")
        _safe(lambda: _seed_alerts(s, data), "alerts")
        _safe(lambda: _seed_mastery(s, data), "mastery_records")
        _safe(lambda: _seed_interventions(s, data), "intervention_plans")
        _safe(lambda: _seed_submissions(s, data), "submissions")
        _safe(lambda: _seed_study_days(s, data), "study_days")
        _safe(lambda: _seed_materials(s, data), "materials")
        _safe(lambda: _seed_templates(s, data), "strategy_templates")
        _safe(lambda: _seed_reports(s, data), "reports")
        _safe(lambda: _seed_graphs(s, data), "graph_nodes/links")
        _safe(lambda: _seed_snapshots(s, data), "view_snapshots")
    _seeded = True


# ---------------------------------------------------------------- 各表播种

def _seed_users(s) -> None:
    if s.query(_m.User).count() > 0:
        return
    colors = {
        "student": "linear-gradient(135deg,#6366f1,#8b5cf6)",
        "teacher": "linear-gradient(135deg,#06b6d4,#0284c7)",
    }
    for login, u in DEMO_USERS.items():
        s.add(_m.User(
            userId=u["userId"], username=login,
            password_hash=u.get("password", "123456"),
            role=u.get("role", "student"), name=u.get("name", ""),
            avatar_char=u.get("avatarChar", ""), org=u.get("org", ""),
            title=u.get("title", ""), dept=u.get("dept", ""),
            avatar_color=colors.get(u.get("role", "student"), ""),
            classes_json=json.dumps(u.get("classes", []), ensure_ascii=False),
        ))
    s.commit()


def _seed_classes(s, data: dict) -> None:
    if s.query(_m.ClassGroup).count() > 0:
        return
    for c in (data.get("teacher") or {}).get("classes", []) or []:
        s.add(_m.ClassGroup(
            classId=c.get("classId", _DEFAULT_CLASS), name=c.get("name", ""),
            studentCount=_to_int(c.get("studentCount", 0)),
            grade=c.get("grade", ""), courseId=_COURSE_ID,
        ))
    s.commit()


def _seed_courses(s, data: dict) -> None:
    if s.query(_m.Course).count() > 0:
        return
    c = data.get("course") or {}
    s.add(_m.Course(
        courseId=c.get("courseId", _COURSE_ID), name=c.get("name", "数据结构"),
        code=c.get("code", ""), teacherId=c.get("teacher", ""),
        term=c.get("term", ""), credit=_to_int(c.get("credit", 0)),
    ))
    s.commit()


def _seed_knowledge_points(s, data: dict) -> None:
    if s.query(_m.KnowledgePoint).count() > 0:
        return
    g = data.get("knowledgeGraph") or {}
    nodes, links = g.get("nodes", []), g.get("links", [])
    kp_detail = data.get("kpDetail") or {}

    # learningPath 提供章节名与学习顺序
    chapter_of, order_of = {}, {}
    for p in data.get("learningPath", []) or []:
        chapter_of[p.get("kpId")] = p.get("chapter", "")
        order_of[p.get("kpId")] = _to_int(p.get("step", 0))

    pre_of, post_of = {}, {}
    for lk in links:
        if lk.get("relation") == "pre":
            pre_of.setdefault(lk.get("target"), []).append(lk.get("source"))
            post_of.setdefault(lk.get("source"), []).append(lk.get("target"))

    for i, n in enumerate(nodes, 1):
        kp_id = n.get("id")
        if not kp_id:
            continue
        detail = kp_detail.get(kp_id) or {}
        pre_ids = [p.get("kpId") for p in (detail.get("pre") or []) if p.get("kpId")]
        post_ids = [p.get("kpId") for p in (detail.get("post") or []) if p.get("kpId")]
        if not pre_ids:
            pre_ids = pre_of.get(kp_id, [])
        if not post_ids:
            post_ids = post_of.get(kp_id, [])
        related = detail.get("relatedProblems") or []
        s.add(_m.KnowledgePoint(
            kpId=kp_id, name=n.get("name", ""), parentId=(pre_ids or [""])[0],
            courseId=_COURSE_ID, chapter=_to_int(n.get("chapter", 0)),
            chapterName=chapter_of.get(kp_id, ""), orderNo=order_of.get(kp_id, i),
            difficulty=_to_int(n.get("difficulty", 1)), isKey=bool(n.get("isKey", False)),
            hours=_to_int(n.get("hours", 0)), type="", status="",
            desc=json.dumps(related, ensure_ascii=False),
            summary=detail.get("summary", n.get("summary", "")),
            preKp=json.dumps(pre_ids, ensure_ascii=False),
            postKp=json.dumps(post_ids, ensure_ascii=False),
        ))
    s.commit()


def _seed_questions(s, data: dict) -> None:
    if s.query(_m.Question).count() > 0:
        return
    # {qId: 已写入来源的优先级}，用于实现「高优先级来源覆盖低优先级来源」
    # （practiceQuestions 带 answer 可判分，必须盖过只有运营字段的 questionBank）
    seen: dict[str, int] = {}
    # 顺序很关键：practiceQuestions 带 answer（可判分）→ questionBank 带运营字段 → 生成题
    for key in ("practiceQuestions", "questionBank", "generatedQuestions"):
        for q in data.get(key, []) or []:
            qid = q.get("qId") or q.get("id")
            if not qid:
                continue
            rank = 0 if key == "practiceQuestions" else (1 if key == "questionBank" else 2)
            prev = seen.get(qid)
            if prev is not None and prev <= rank:
                continue          # 已存在更高优先级的版本
            seen[qid] = rank
            if prev is not None:  # 用高优先级版本覆盖低优先级
                row = s.get(_m.Question, qid)
                if row is None:
                    continue
            else:
                row = _m.Question(qId=qid)
                s.add(row)
            opts = q.get("options")
            row.kpId = q.get("kpId", row.kpId or "")
            row.type = q.get("type", row.type or "choice")
            row.stem = q.get("stem", row.stem or "")
            row.options_json = json.dumps(opts if isinstance(opts, list) else [], ensure_ascii=False)
            row.answer = str(q.get("answer", row.answer or ""))
            row.analysis = q.get("analysis", row.analysis or "")
            row.difficulty = _to_int(q.get("difficulty", row.difficulty or 1))
            row.source = q.get("source", row.source or "")
            row.status = q.get("status", row.status or "published")
            row.isKey = bool(q.get("isKey", row.isKey))
            row.useCount = _to_int(q.get("useCount", row.useCount or 0))
            row.createdAt = _norm_ts(q.get("createdAt", row.createdAt or ""))

    s.flush()

    # wrongDetail 带完整题干/选项/答案/前置知识点，补足 questionBank 仅有运营字段的空洞
    for qid, wd in (data.get("wrongDetail") or {}).items():
        row = s.get(_m.Question, qid)
        if row is None:
            row = _m.Question(qId=qid)
            s.add(row)
        opts = wd.get("options")
        if isinstance(opts, list) and opts:
            row.options_json = json.dumps(opts, ensure_ascii=False)
        row.kpId = wd.get("kpId", row.kpId or "")
        row.type = wd.get("type", row.type or "single")
        row.stem = wd.get("stem", row.stem or "")
        row.answer = str(wd.get("answer", row.answer or ""))
        row.analysis = wd.get("analysis", row.analysis or "")
        row.difficulty = _to_int(wd.get("difficulty", row.difficulty or 1))
        row.isKey = bool(wd.get("isKey", row.isKey))
        row.createdAt = row.createdAt or _now()
        if wd.get("preKp") and row.kpId:
            kp = s.get(_m.KnowledgePoint, row.kpId)
            if kp is not None and not json.loads(kp.preKp or "[]"):
                kp.preKp = json.dumps(wd.get("preKp"), ensure_ascii=False)
        # 相似题也落库，保证错题详情里的「同类题推荐」有真实数据
        for sim in wd.get("similar", []) or []:
            sim_id = sim.get("qId")
            if not sim_id:
                continue
            if s.get(_m.Question, sim_id) is None:
                s.add(_m.Question(
                    qId=sim_id, kpId=row.kpId or "", type="single",
                    stem=sim.get("stem", ""), options_json="[]", answer="",
                    analysis="", difficulty=row.difficulty or 1, source="wrongDetail",
                    status="published", isKey=False, useCount=0,
                    createdAt=_now(),
                ))
    s.commit()


def _seed_resources(s, data: dict) -> None:
    if s.query(_m.Resource).count() > 0:
        return
    seen: set[str] = set()

    def add(rid: str, title: str, type_: str, kp: str, kp_id: str, source: str,
            views: int, progress: int, duration: str, pages: int, count: int) -> None:
        if not rid or rid in seen or s.get(_m.Resource, rid) is not None:
            return
        seen.add(rid)
        s.add(_m.Resource(
            resId=rid, title=title, type=type_, kp=kp, kpId=kp_id, source=source,
            views=views, progress=progress, duration=duration, pages=pages, count=count,
        ))

    for r in data.get("resources", []) or []:
        rid = r.get("resId") or r.get("id")
        add(rid=rid, title=r.get("title", ""), type_=r.get("type", "video"),
            kp=r.get("kp", ""), kp_id=r.get("kpId", ""), source=r.get("source", ""),
            views=_to_int(r.get("views", 0)), progress=_to_int(r.get("progress", 0)),
            duration=str(r.get("duration", "") or ""), pages=_to_int(r.get("pages", 0)),
            count=_to_int(r.get("count", 0)))

    # 知识点详情中的配套资源单独以 kpId 落库，供 /graph/kp/{kpId} 直接查询
    for kp_id, d in (data.get("kpDetail") or {}).items():
        for r in d.get("resources", []) or []:
            add(rid=r.get("resId", ""), title=r.get("title", ""),
                type_=r.get("type", "video"), kp=r.get("source", ""), kp_id=kp_id,
                source=r.get("source", ""), views=0,
                progress=_to_int(r.get("progress", 0)),
                duration=str(r.get("duration", "") or ""),
                pages=_to_int(r.get("pages", 0)), count=0)

    # 错题详情里的配套资源同样落库，供 /practice/wrong-book/{qId}/detail 使用
    for qid, wd in (data.get("wrongDetail") or {}).items():
        qq = s.get(_m.Question, qid)
        kp_id = qq.kpId if qq else ""
        for i, r in enumerate(wd.get("resources", []) or []):
            meta = str(r.get("meta", "") or "")
            duration = meta if ":" in meta else ""
            pages = _to_int(meta.split("·")[-1].strip().rstrip("p")) if "p" in meta.lower() else 0
            add(rid=f"WD-{qid}-{i}", title=r.get("name", ""),
                type_=r.get("type", "video"), kp=r.get("name", ""), kp_id=kp_id,
                source="错题推荐", views=0, progress=0, duration=duration, pages=pages, count=0)
    s.commit()


def _seed_messages(s, data: dict) -> None:
    if s.query(_m.Message).count() > 0:
        return
    for m in data.get("messages", []) or []:
        s.add(_m.Message(
            msgId=m.get("msgId", ""), userId=m.get("userId", _DEMO_STUDENT),
            sender=m.get("from", "系统"), to=m.get("to", ""),
            title=m.get("title", ""), content=m.get("content", ""),
            time=_norm_ts(m.get("time", "")), read=bool(m.get("read", False)),
        ))
    s.commit()


def _seed_students(s, data: dict) -> None:
    if s.query(_m.Student).count() > 0:
        return
    class_name = ((data.get("teacherDashboard") or {}).get("classOverview") or {}).get("className", "")
    for st in data.get("students", []) or []:
        uid = st.get("userId")
        if not uid:
            continue
        s.add(_m.Student(
            userId=uid, name=st.get("name", ""), no=st.get("no", ""),
            avatar=st.get("avatar", ""), classId=st.get("classId", _DEFAULT_CLASS),
            className=class_name,
            completionRate=_to_float(st.get("completion", 0)),
            masteryRate=_to_float(st.get("mastery", 0)),
            goalAchieveRate=_to_float(st.get("goal", 0)),
            activeRate=_to_float(st.get("activeRate", 0)),
            alertLevel=st.get("alertLevel", "green"),
            alertCount=_to_int(st.get("alertCount", 0)),
            lastActive=st.get("lastActive", ""),
            studyMinutes=_to_int(st.get("studyMinutes", 0)),
            rank=_to_int(st.get("rank", 0)),
        ))
    s.commit()


def _seed_alerts(s, data: dict) -> None:
    if s.query(_m.Alert).count() > 0:
        return
    seen = set()
    # 教师预警带 userId + 学生姓名，优先入库（班级视角完整）
    for a in data.get("teacherAlerts", []) or []:
        aid = a.get("alertId")
        if not aid or aid in seen:
            continue
        seen.add(aid)
        s.add(_m.Alert(
            alertId=aid, studentId=a.get("userId", ""), studentName=a.get("student", ""),
            type=a.get("type", ""), level=a.get("level", "info"),
            title=a.get("title", a.get("desc", "")),
            desc=a.get("desc", ""), trigger=a.get("trigger", ""),
            kpId=a.get("kpId", ""), kp=a.get("kp", ""),
            detail_json="{}", suggestions_json="[]",
            trend_json=json.dumps(a.get("trendData", []), ensure_ascii=False),
            createdAt=_norm_ts(a.get("createdAt", "")),
            status=a.get("status", "open"), read=a.get("status") == "reviewed",
        ))
    s.flush()
    # 学生预警结构化程度更高（含 detail / suggestions），同名 id 不重复
    for a in data.get("studentAlerts", []) or []:
        aid = a.get("alertId")
        if not aid:
            continue
        row = None
        if aid in seen:
            # 同一预警在教师端已建行，这里只做「结构化字段回填」：
            # 教师端那条只有标题/趋势，detail/suggestions 必须从学生端版本补齐，
            # 否则学生端预警详情面板整块空白。
            row = s.query(_m.Alert).filter_by(alertId=aid).first()
            if row is None:
                continue
        else:
            seen.add(aid)
            row = _m.Alert(alertId=aid, studentId=a.get("userId", _DEMO_STUDENT),
                           studentName="", trend_json="[]")
            s.add(row)
        row.type = a.get("type", row.type)
        row.level = a.get("level", row.level)
        row.title = a.get("title", row.title)
        row.desc = a.get("desc", row.desc)
        row.trigger = a.get("trigger", row.trigger)
        row.kpId = a.get("kpId", row.kpId)
        row.kp = a.get("kp", row.kp)
        row.detail_json = json.dumps(a.get("detail") or {}, ensure_ascii=False)
        row.suggestions_json = json.dumps(a.get("suggestions") or [], ensure_ascii=False)
        row.createdAt = _norm_ts(a.get("createdAt", "")) or row.createdAt
        row.status = a.get("status", row.status)
        row.read = a.get("status") == "reviewed"
    s.commit()


def _seed_mastery(s, data: dict) -> None:
    """掌握度种子：演示学生取自 masteryMatrix（精度高），其余取自 heatmap。"""
    if s.query(_m.MasteryRecord).count() > 0:
        return
    kps = s.query(_m.KnowledgePoint).all()
    resolve_kp = _build_kp_resolver(kps)
    name_to_uid = {st.name: st.userId for st in s.query(_m.Student).all()}

    def add(student_id, kp_id, mastery, completion=None):
        if not student_id or not kp_id:
            return
        s.add(_m.MasteryRecord(
            studentId=student_id, kpId=kp_id, mastery=_to_float(mastery),
            correctRate=_to_float(mastery),
            completion=_to_float(completion if completion is not None else mastery),
            status="",
        ))

    # 1) 演示学生：掌握矩阵（真实 kpId）
    for ch in data.get("masteryMatrix", []) or []:
        for it in ch.get("items", []) or []:
            add(_DEMO_STUDENT, it.get("kpId"), it.get("mastery", 0), it.get("completion"))

    # 2) 全班：热力图（姓名轴 → ID）
    hm = data.get("heatmap") or {}
    kp_axis, stu_axis = hm.get("kpAxis", []) or [], hm.get("studentAxis", []) or []
    for row in hm.get("data", []) or []:
        if len(row) < 3:
            continue
        kp_idx, stu_idx, val = row[0], row[1], row[2]
        kp_id = resolve_kp(kp_axis[kp_idx]) if 0 <= kp_idx < len(kp_axis) else ""
        uid = name_to_uid.get(stu_axis[stu_idx], "") if 0 <= stu_idx < len(stu_axis) else ""
        if uid == _DEMO_STUDENT:      # 演示学生已有更精确的数据
            continue
        add(uid, kp_id, val)
    s.commit()


def _seed_interventions(s, data: dict) -> None:
    if s.query(_m.InterventionPlan).count() > 0:
        return
    for iv in data.get("interventions", []) or []:
        iv_id = iv.get("ivId") or iv.get("id")
        if not iv_id:
            continue
        s.add(_m.InterventionPlan(
            planId=iv_id, studentId=iv.get("studentId", ""), teacherId="",
            type=iv.get("type", "common"), scope=iv.get("scope", "common"),
            level=iv.get("level", "warn"), alertId=iv.get("alertId", ""),
            title=iv.get("title", ""), target=iv.get("target", ""),
            reason=iv.get("reason", ""),
            content=json.dumps(iv.get("steps", []), ensure_ascii=False),
            resources_json=json.dumps(iv.get("resources", []), ensure_ascii=False),
            expectEffect=iv.get("expectEffect", ""), packId=iv.get("packId", ""),
            status=iv.get("status", "pending"),
            createdAt=_norm_ts(iv.get("createdAt", "")),
        ))
    s.commit()


def _seed_submissions(s, data: dict) -> None:
    """历史作答：错题本（真实条目）+ 由掌握度反推的合成记录（确定性）。"""
    if s.query(_m.Submission).count() > 0:
        return
    rng = random.Random(20260828)
    today = datetime(2026, 8, 28, 21, 0)

    # 1) 错题本：真实条目原样落库
    for w in data.get("wrongBook", []) or []:
        qid = w.get("qId")
        if not qid:
            continue
        for i in range(max(1, _to_int(w.get("wrongCount", 1)))):
            s.add(_m.Submission(
                studentId=_DEMO_STUDENT, qId=qid, answer=w.get("myAnswer", ""),
                correct=False, score=0.0, ts=_norm_ts(w.get("lastTime", "")),
                duration=60 + rng.randint(0, 120), mastered=bool(w.get("mastered", False)),
                errorType=w.get("errorType", ""),
            ))

    # 2) 合成历史：按掌握度生成，保证「题量 / 正确数 / 用时」与掌握度自洽
    q_by_kp = {}
    for q in s.query(_m.Question).filter(_m.Question.answer != "").all():
        q_by_kp.setdefault(q.kpId, []).append(q)
    for rec in s.query(_m.MasteryRecord).all():
        pool = q_by_kp.get(rec.kpId) or []
        if not pool:
            continue
        mastery = max(0.0, min(100.0, rec.mastery))
        n = max(3, min(20, round(mastery / 6)))
        ok_n = round(n * mastery / 100)
        for i in range(n):
            q = pool[rng.randrange(len(pool))]
            correct = i < ok_n
            day = today - timedelta(days=rng.randint(1, 75))
            s.add(_m.Submission(
                studentId=rec.studentId, qId=q.qId,
                answer=q.answer if correct else _wrong_pick(q, rng),
                correct=correct, score=100.0 if correct else 0.0,
                ts=day.strftime("%Y-%m-%d %H:%M"),
                duration=rng.randint(25, 180), mastered=False,
                errorType="" if correct else "概念性错误",
            ))
    s.commit()


def _wrong_pick(q, rng) -> str:
    """从选项中挑一个明显错误的答案作为历史错答。"""
    try:
        opts = json.loads(q.options_json or "[]")
    except Exception:
        opts = []
    keys = [o.get("key") for o in opts if isinstance(o, dict) and o.get("key")]
    keys = [k for k in keys if str(k).strip().upper() != str(q.answer).strip().upper()]
    return keys[rng.randrange(len(keys))] if keys else "X"


def _seed_study_days(s, data: dict) -> None:
    """学习日历：演示学生用 mock 的 364 天贡献图，其余按学习时长确定性分布。"""
    if s.query(_m.StudyDay).count() > 0:
        return
    rng = random.Random(20260901)
    ov = ((data.get("studentDashboard") or {}).get("overview") or {})
    start = ov.get("streakHistoryStart", "2025-09-22")
    hist = ov.get("streakHistory", []) or []
    try:
        y, m, d = [int(x) for x in start.split("-")]
        base = datetime(y, m, d)
    except Exception:
        base = datetime(2025, 9, 22)
    for i, v in enumerate(hist):
        if not v:
            continue
        s.add(_m.StudyDay(studentId=_DEMO_STUDENT, day=(base + timedelta(days=i)).strftime("%Y-%m-%d"),
                          minutes=_to_int(v) * 35, questions=_to_int(v) * 3))
    end = datetime(2026, 8, 28)
    for st in s.query(_m.Student).all():
        if st.userId == _DEMO_STUDENT:
            continue
        total = max(60, st.studyMinutes or 240)
        days = 90
        for i in range(days):
            day = end - timedelta(days=i)
            if rng.random() > 0.72:          # 约 72% 的日子有学习
                continue
            minutes = max(10, round(total / days * rng.uniform(0.6, 1.6)))
            s.add(_m.StudyDay(studentId=st.userId, day=day.strftime("%Y-%m-%d"),
                              minutes=minutes, questions=max(1, round(minutes / 12))))
    s.commit()


def _seed_materials(s, data: dict) -> None:
    if s.query(_m.Material).count() > 0:
        return
    cfg = data.get("genConfig") or {}
    for i, m in enumerate(cfg.get("materials", []) or []):
        s.add(_m.Material(
            fileId=m.get("fileId", f"F{1000 + i}"), name=m.get("name", ""),
            size=m.get("size", ""), type=m.get("type", "doc"),
            status=m.get("status", "parsed"), kpCount=_to_int(m.get("kpCount", 0)),
            progress=100 if m.get("status") == "parsed" else 0,
            uploadedAt="2026-08-20",
        ))
    s.commit()


def _seed_templates(s, data: dict) -> None:
    if s.query(_m.StrategyTemplate).count() > 0:
        return
    for t in data.get("strategyTemplates", []) or []:
        tid = t.get("tplId")
        if not tid:
            continue
        s.add(_m.StrategyTemplate(
            tplId=tid, name=t.get("name", ""), scene=t.get("scene", ""),
            desc=t.get("desc", ""), useCount=_to_int(t.get("useCount", 0)),
            successRate=_to_int(t.get("successRate", 0)),
            avgLift=_to_float(t.get("avgLift", 0)),
            tags_json=json.dumps(t.get("tags", []), ensure_ascii=False),
        ))
    s.commit()


def _seed_reports(s, data: dict) -> None:
    if s.query(_m.Report).count() > 0:
        return
    detail = data.get("reportDetail") or {}
    for r in data.get("reportList", []) or []:
        rid = r.get("reportId")
        if not rid:
            continue
        s.add(_m.Report(
            reportId=rid, title=r.get("title", ""), scope=r.get("scope", ""),
            period=r.get("period", ""), createdAt=_norm_ts(r.get("createdAt", "")),
            creator=r.get("creator", ""), status=r.get("status", "ready"),
            pages=_to_int(r.get("pages", 0)), classId=_DEFAULT_CLASS,
            meta_json=json.dumps(detail.get("meta", {}), ensure_ascii=False),
            sections_json=json.dumps(detail.get("sections", []), ensure_ascii=False),
        ))
    s.commit()


def _seed_graphs(s, data: dict) -> None:
    """图谱结构与静态属性入库；动态属性（掌握率等）由 services/graph 实时覆盖。

    kpIds 是「图谱节点 ↔ 知识点」的业务映射，写在种子里：
      - 目标图谱用它算达成度（关联知识点的平均掌握率）
      - 问题图谱用它算错误率（关联知识点的真实答错占比）
    """
    if s.query(_m.GraphNode).count() > 0:
        return
    for gtype, key in (("knowledge", "knowledgeGraph"), ("problem", "problemGraph"), ("goal", "goalGraph")):
        mapping = _GOAL_KP if gtype == "goal" else (_PROBLEM_KP if gtype == "problem" else {})
        g = data.get(key) or {}
        for i, n in enumerate(g.get("nodes", []) or []):
            payload = {k: v for k, v in n.items() if k not in ("id", "name", "category")}
            payload["kpIds"] = mapping.get(n.get("id"), [])
            s.add(_m.GraphNode(graphType=gtype, nodeId=n.get("id", ""), name=n.get("name", ""),
                               category=_to_int(n.get("category", 0)), orderNo=i,
                               payload_json=json.dumps(payload, ensure_ascii=False)))
        for lk in g.get("links", []) or []:
            s.add(_m.GraphLink(graphType=gtype, sourceId=lk.get("source", ""), targetId=lk.get("target", ""),
                               relation=lk.get("relation", "pre")))
    s.commit()


def _seed_snapshots(s, data: dict) -> None:
    """仅 AI 会话历史等暂缓模块仍读快照；其余端点不再依赖它。"""
    if s.query(_m.ViewSnapshot).count() > 0:
        return
    for k in ("chatHistory", "chatMessages", "teachingMethods"):
        if k in data:
            s.add(_m.ViewSnapshot(key=k, payload_json=json.dumps(data[k], ensure_ascii=False)))
    s.commit()


# ---------------------------------------------------------------- 对外接口

def seed(key: str, default=None):
    """读取快照（仅供 AI 暂缓模块使用）。新代码请走 repo / services。"""
    ensure_db()
    with SessionLocal() as s:
        row = s.get(_m.ViewSnapshot, key)
        if row is None:
            return default
        return json.loads(row.payload_json)


def get_user_by_username(username: str):
    ensure_db()
    with SessionLocal() as s:
        return s.query(_m.User).filter_by(username=username).first()


def get_user_by_id(user_id: str):
    ensure_db()
    with SessionLocal() as s:
        return s.query(_m.User).filter_by(userId=user_id).first()


def reset_db() -> None:
    """开发期：丢弃全部数据并按最新模型重建（生产请走 Alembic）。"""
    global _seeded
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _seeded = False
    ensure_db()
