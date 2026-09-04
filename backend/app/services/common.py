"""查询服务公共工具。

放在 services 层的通用计算（掌握度、等级、班级聚合、作答统计）集中在此，
避免各 service 重复写 SQL。所有函数都是**纯读**，不写库。
"""
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from ..db import models as _m

# ---------------------------------------------------------------- 基础

def now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def round1(v, default=0.0) -> float:
    try:
        return round(float(v), 1)
    except Exception:
        return default


def pct(part, total, default=0.0) -> float:
    return round1(part / total * 100, default) if total else default


def level_of(v) -> str:
    """与前端 common.js:U.level 完全一致的五级划分。"""
    try:
        v = float(v)
    except Exception:
        return "none"
    if v <= 0:
        return "none"
    if v >= 85:
        return "excellent"
    if v >= 75:
        return "good"
    if v >= 60:
        return "fair"
    return "weak"


def parse_ts(v: str):
    """解析 'YYYY-MM-DD HH:MM' / 'YYYY-MM-DD'。

    统一返回 **UTC 感知** datetime：本库所有时间字符串都按 UTC 落盘
    （now_str 用 datetime.now(timezone.utc)），若这里返回朴素时间，
    后面与时间差计算（time_ago / trend_of）会抛
    "can't subtract offset-naive and offset-aware datetimes"。
    """
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(v)[:16], fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def day_str(d: datetime) -> str:
    return d.strftime("%Y-%m-%d")


def today_str() -> str:
    return day_str(datetime.now(timezone.utc))


# ---------------------------------------------------------------- 维度查询

def student_ids_of(s, class_id: str = "") -> list:
    q = s.query(_m.Student.userId)
    if class_id:
        q = q.filter(_m.Student.classId == class_id)
    return [r[0] for r in q.all()]


def kp_index(s) -> dict:
    return {kp.kpId: kp for kp in s.query(_m.KnowledgePoint).all()}


def kp_name(s, kp_id: str, fallback="") -> str:
    kp = s.get(_m.KnowledgePoint, kp_id)
    return kp.name if kp else (fallback or kp_id)


def mastery_of(s, student_id: str) -> dict:
    """{kpId: mastery}"""
    rows = s.query(_m.MasteryRecord).filter_by(studentId=student_id).all()
    return {r.kpId: r.mastery for r in rows}


def class_kp_mastery(s, student_ids: list) -> dict:
    """{kpId: 班级平均掌握率}"""
    if not student_ids:
        return {}
    rows = (s.query(_m.MasteryRecord.kpId, func.avg(_m.MasteryRecord.mastery))
            .filter(_m.MasteryRecord.studentId.in_(student_ids))
            .group_by(_m.MasteryRecord.kpId).all())
    return {k: round1(v) for k, v in rows}


def kp_question_count(s) -> dict:
    rows = s.query(_m.Question.kpId, func.count(_m.Question.qId)).group_by(_m.Question.kpId).all()
    return {k: v for k, v in rows}


def submissions_of(s, student_ids: list):
    if not student_ids:
        return []
    return s.query(_m.Submission).filter(_m.Submission.studentId.in_(student_ids)).all()


def kp_of_questions(s) -> dict:
    return {q.qId: q.kpId for q in s.query(_m.Question.qId, _m.Question.kpId).all()}


def kp_stats(s, student_id: str) -> dict:
    """{kpId: {questions, correct, wrong, minutes, accuracy}}"""
    q2kp = kp_of_questions(s)
    out = {}
    for sub in s.query(_m.Submission).filter_by(studentId=student_id).all():
        kp = q2kp.get(sub.qId, "")
        st = out.setdefault(kp, {"questions": 0, "correct": 0, "wrong": 0, "minutes": 0})
        st["questions"] += 1
        st["correct" if sub.correct else "wrong"] += 1
        st["minutes"] += int(sub.duration or 0)
    for st in out.values():
        st["accuracy"] = pct(st["correct"], st["questions"])
    return out


def accuracy_of(s, student_id: str) -> float:
    total = s.query(func.count(_m.Submission.id)).filter_by(studentId=student_id).scalar() or 0
    if not total:
        return 0.0
    ok = s.query(func.count(_m.Submission.id)).filter_by(studentId=student_id, correct=True).scalar() or 0
    return pct(ok, total)


def recent_submissions(s, student_ids: list, limit: int = 8):
    if not student_ids:
        return []
    return (s.query(_m.Submission)
            .filter(_m.Submission.studentId.in_(student_ids))
            .order_by(_m.Submission.id.desc()).limit(limit).all())


def study_minutes_on(s, student_id: str, day: str) -> int:
    row = s.query(_m.StudyDay).filter_by(studentId=student_id, day=day).first()
    return int(row.minutes) if row else 0


def trend_of(s, student_id: str, kp_id: str = "", buckets: int = 5, span_days: int = 60) -> list:
    """近 N 段的正确率趋势（每段 span_days/buckets 天），用于预警趋势与效果曲线。"""
    q2kp = kp_of_questions(s)
    end = datetime.now(timezone.utc)
    step = max(1, span_days // max(1, buckets))
    buckets_acc = [[] for _ in range(buckets)]
    subs = s.query(_m.Submission).filter_by(studentId=student_id).all()
    for sub in subs:
        if kp_id and q2kp.get(sub.qId) != kp_id:
            continue
        dt = parse_ts(sub.ts)
        if not dt:
            continue
        idx = (end - dt).days // step
        if 0 <= idx < buckets:
            buckets_acc[buckets - 1 - idx].append(1.0 if sub.correct else 0.0)
    out = []
    prev = None
    for acc in buckets_acc:
        val = round1(sum(acc) / len(acc) * 100) if acc else (prev if prev is not None else 0.0)
        out.append(val)
        prev = val
    return out


def jload(text, default):
    try:
        return json.loads(text) if text else default
    except Exception:
        return default


def time_ago(v: str) -> str:
    """把 'YYYY-MM-DD HH:MM' 转成 'x 分钟前 / x 小时前 / x 天前'。"""
    dt = parse_ts(v)
    if not dt:
        return ""
    delta = datetime.now(timezone.utc) - dt
    mins = int(delta.total_seconds() // 60)
    if mins < 1:
        return "刚刚"
    if mins < 60:
        return f"{mins} 分钟前"
    if mins < 1440:
        return f"{mins // 60} 小时前"
    days = mins // 1440
    return f"{days} 天前" if days < 30 else v[:10]
