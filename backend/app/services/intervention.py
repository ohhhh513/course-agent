"""干预服务：干预效果验证 + 策略模板库。

干预效果用**真实作答数据**做前后对比：
以干预创建时间为基准划分 6 个时间窗（干预前 → 干预后），
统计「干预组」（干预对象）与「对照组」（其余学生）在每个窗口的正确率，
得到真实的提升曲线与提升差值。
"""
import json
import uuid
from datetime import datetime, timedelta, timezone

from ..db import models as _m
from ..db.session import SessionLocal
from .common import jload, now_str, parse_ts, pct, round1, student_ids_of

# 6 个观察窗口：(标签, 起始偏移天数, 结束偏移天数)  相对干预创建日
_WINDOWS = [
    ("干预前3日", -5, -3), ("干预前1日", -3, -1), ("干预日", -1, 0),
    ("干预后1日", 0, 1), ("干预后3日", 1, 3), ("干预后7日", 3, 7),
]


def intervention_effect(iv_id: str, class_id: str = "CL2301") -> dict:
    with SessionLocal() as s:
        plan = (s.query(_m.InterventionPlan).filter_by(planId=iv_id).first()
                or s.query(_m.InterventionPlan).order_by(_m.InterventionPlan.id.desc()).first())
        if not plan:
            return {}
        # 注意：不能回退到 datetime.utcnow()（朴素时间），
        # 否则下面与 parse_ts 得到的 UTC 感知时间相减会抛 TypeError
        base = parse_ts(plan.createdAt) or datetime.now(timezone.utc)

        ids = student_ids_of(s, class_id)
        target_ids = [plan.studentId] if plan.studentId else []
        if not target_ids:                       # 班级级干预：取目标知识点落后的学生
            target_ids = [r.studentId for r in s.query(_m.MasteryRecord)
                          .filter(_m.MasteryRecord.mastery < 60).all()]
        target_set = set(target_ids) or set(ids)
        ctrl_ids = [i for i in ids if i not in target_set] or ids

        q2kp = {q.qId: q.kpId for q in s.query(_m.Question.qId, _m.Question.kpId).all()}
        kp_ids = json.loads(plan.content or "[]") and None  # steps 不是知识点，忽略
        subs = s.query(_m.Submission).all()

        def bucket(student_set):
            acc = [[] for _ in _WINDOWS]
            for x in subs:
                if x.studentId not in student_set:
                    continue
                dt = parse_ts(x.ts)
                if not dt:
                    continue
                offset = (dt - base).days
                for i, (_, lo, hi) in enumerate(_WINDOWS):
                    if lo <= offset < hi:
                        acc[i].append(1.0 if x.correct else 0.0)
                        break
            out, prev = [], None
            for a in acc:
                val = pct(sum(a), len(a), prev if prev is not None else 0.0)
                out.append(val)
                prev = val
            return out

        exp = bucket(target_set)
        ctrl = bucket(set(ctrl_ids))
        lift = round1(exp[-1] - exp[0]) if exp else 0.0
        lift_ctrl = round1(ctrl[-1] - ctrl[0]) if ctrl else 0.0

        return {
            "ivId": plan.planId,
            "xAxis": [w[0] for w in _WINDOWS],
            "series": [
                {"name": "干预组掌握率", "data": exp, "color": "#22c55e"},
                {"name": "对照组掌握率", "data": ctrl, "color": "#64748b"},
            ],
            "summary": (
                f"干预组在观察窗口内正确率由 {exp[0]}% 变化到 {exp[-1]}%（{lift:+}pp），"
                f"同期对照组由 {ctrl[0]}% 变化到 {ctrl[-1]}%（{lift_ctrl:+}pp），"
                f"净提升 {round1(lift - lift_ctrl)}pp。"
                f"{'干预有效性显著。' if lift - lift_ctrl > 5 else '建议延长观察期或加大干预强度。'}"
            ),
        }


def list_templates(scene: str = "", keyword: str = "") -> list:
    with SessionLocal() as s:
        q = s.query(_m.StrategyTemplate)
        if scene and scene != "all":
            q = q.filter(_m.StrategyTemplate.scene.contains(scene))
        if keyword:
            q = q.filter(_m.StrategyTemplate.name.contains(keyword))
        rows = q.order_by(_m.StrategyTemplate.useCount.desc()).all()
        return [{
            "tplId": r.tplId, "name": r.name, "scene": r.scene, "desc": r.desc,
            "useCount": r.useCount, "successRate": r.successRate,
            "avgLift": r.avgLift, "tags": jload(r.tags_json, []),
        } for r in rows]


def save_template(payload: dict) -> dict:
    p = payload or {}
    tid = p.get("tplId") or ("TPL" + uuid.uuid4().hex[:6].upper())
    with SessionLocal() as s:
        row = s.get(_m.StrategyTemplate, tid)
        if row is None:
            row = _m.StrategyTemplate(tplId=tid)
            s.add(row)
        row.name = p.get("name", row.name or "")
        row.scene = p.get("scene", row.scene or "通用")
        row.desc = p.get("desc", row.desc or "")
        row.useCount = int(p.get("useCount", row.useCount or 0) or 0)
        row.successRate = int(p.get("successRate", row.successRate or 0) or 0)
        row.avgLift = float(p.get("avgLift", row.avgLift or 0) or 0)
        row.tags_json = json.dumps(p.get("tags", jload(row.tags_json, [])), ensure_ascii=False)
        s.commit()
        return {"tplId": tid, "name": row.name, "ok": True, "createdAt": now_str()}
