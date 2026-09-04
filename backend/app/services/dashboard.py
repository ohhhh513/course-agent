"""驾驶舱聚合服务（学生端 / 教师端）。

所有数值均由真实表计算，不做任何硬编码：
  - 学习日历：study_days（364 天贡献图）
  - 掌握度：mastery_records
  - 待办 / 动态：alerts + submissions + messages + intervention_plans 实时推导
  - 班级概览：students 档案 + submissions 近 7 日环比
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from ..db import models as _m
from ..db.session import SessionLocal
from .common import (
    class_kp_mastery, kp_index, kp_stats, level_of, now_str, parse_ts, pct,
    round1, student_ids_of, time_ago, today_str,
)

_WEEKS = 52
_DAYS = _WEEKS * 7


def _streak_level(minutes: int) -> int:
    """分钟数 → 贡献图强度 0~4（与前端 GitHub 风格图例一致）。"""
    if minutes <= 0:
        return 0
    if minutes < 20:
        return 1
    if minutes < 40:
        return 2
    if minutes < 70:
        return 3
    return 4


def _streak_of(s, student_id: str) -> dict:
    """由 study_days 还原连续学习数据（长度固定 364，末位为今天）。"""
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=_DAYS - 1)
    rows = {r.day: r for r in s.query(_m.StudyDay).filter_by(studentId=student_id).all()}
    history, minutes_today = [], 0
    for i in range(_DAYS):
        day = (start + timedelta(days=i)).isoformat()
        row = rows.get(day)
        m = int(row.minutes) if row else 0
        history.append(_streak_level(m))
        if i == _DAYS - 1:
            minutes_today = m
    cur = mx = run = total = 0
    for v in history:
        if v:
            run += 1
            total += 1
            mx = max(mx, run)
        else:
            run = 0
    cur = 0
    for v in reversed(history):
        if not v:
            break
        cur += 1
    return {
        "streakDays": cur, "streakHistoryStart": start.isoformat(),
        "streakHistory": history, "currentStreak": cur, "maxStreak": mx,
        "totalDays": total, "todayStudyMinutes": minutes_today,
    }


# ---------------------------------------------------------------- 学生驾驶舱

def student_dashboard(student_id: str) -> dict:
    with SessionLocal() as s:
        st = s.get(_m.Student, student_id)
        kps = kp_index(s)
        recs = s.query(_m.MasteryRecord).filter_by(studentId=student_id).all()
        mastery = {r.kpId: r.mastery for r in recs}
        completion = {r.kpId: r.completion for r in recs}
        stats = kp_stats(s, student_id)
        q2kp = {q.qId: q.kpId for q in s.query(_m.Question.qId, _m.Question.kpId).all()}

        # ---- overview
        ordered = sorted(kps.values(), key=lambda k: (k.orderNo, k.kpId))
        course_progress = round1(sum(completion.values()) / len(completion)) if completion else 0.0
        current = next((k for k in ordered if mastery.get(k.kpId, 0) < 85), ordered[-1] if ordered else None)
        streak = _streak_of(s, student_id)

        open_alerts = (s.query(_m.Alert).filter_by(studentId=student_id, status="open")
                       .order_by(_m.Alert.id.desc()).all())
        red = [a for a in open_alerts if a.level == "red"]
        status = "danger" if red else ("warn" if open_alerts else "ok")

        overview = {
            "courseProgress": course_progress or round1(st.completionRate if st else 0),
            "currentNode": {"kpId": current.kpId if current else "", "name": current.name if current else ""},
            **streak,
            "status": status,
        }

        # ---- coreMetrics
        avg_mastery = round1(sum(mastery.values()) / len(mastery)) if mastery else 0.0
        core_metrics = {
            "completionRate": overview["courseProgress"],
            "masteryRate": avg_mastery,
            "goalAchieveRate": round1(st.goalAchieveRate if st else avg_mastery),
            "updatedAt": now_str(),
        }

        # ---- 薄弱点（掌握率 < 70）
        weak = sorted((k for k in ordered if 0 < mastery.get(k.kpId, 0) < 70),
                      key=lambda k: mastery.get(k.kpId, 0))[:3]
        weak_points = []
        for k in weak:
            st_kp = stats.get(k.kpId, {})
            wrong = st_kp.get("wrong", 0)
            acc = st_kp.get("accuracy", 0.0)
            weak_points.append({
                "kpId": k.kpId, "name": k.name,
                "masteryRate": round(mastery.get(k.kpId, 0)),
                "chapter": k.chapterName or (f"第{k.chapter}章" if k.chapter else ""),
                "errorCount": wrong,
                "trend": round1(acc - mastery.get(k.kpId, 0)),
                "level": "danger" if mastery.get(k.kpId, 0) < 60 else "warn",
            })

        # ---- 待办（按优先级拼接，最多 4 条）
        todos = []
        if current:
            todos.append({
                "id": "TD1", "type": "recommend", "level": "brand",
                "title": f"今日推荐学习：{current.name}",
                "desc": f"预计 {current.hours or 2} 学时 · 当前掌握 {round(mastery.get(current.kpId, 0))}%",
                "action": "开始学习", "target": "learn", "kpId": current.kpId,
            })
        unread_msg = s.query(func.count(_m.Message.id)).filter_by(userId=student_id, read=False).scalar() or 0
        if unread_msg:
            todos.append({
                "id": "TD2", "type": "message", "level": "brand",
                "title": f"教师发来 {unread_msg} 条新消息", "desc": "关于薄弱知识点的学习建议",
                "action": "去查看", "target": "messages", "kpId": "",
            })
        if weak_points:
            w = weak_points[0]
            todos.append({
                "id": "TD3", "type": "alert", "level": w["level"],
                "title": f"预警：{w['name']} 掌握率 {w['masteryRate']}%",
                "desc": f"累计错 {w['errorCount']} 题，建议优先补救",
                "action": "去补救", "target": "alerts", "kpId": w["kpId"],
            })
        wrong_qs = s.query(_m.Submission.qId).filter_by(studentId=student_id, correct=False, mastered=False).distinct().count()
        if wrong_qs:
            todos.append({
                "id": "TD4", "type": "practice", "level": "ok",
                "title": f"错题重练：{wrong_qs} 道错题待攻克",
                "desc": "重做错题并标记掌握后自动移出错题本",
                "action": "去重练", "target": "practice", "kpId": "",
            })

        # ---- 猜你想问
        suggested = [f"「{w['name']}」的核心思路是什么？" for w in weak_points[:3]]
        suggested += ["帮我梳理本章的知识脉络", "这类题我总错，能给我一道类似的练习吗？"]
        suggested = suggested[:5]

        # ---- 最近动态（练习 / 预警 / 消息 合并，按时间倒序）
        acts = []
        for sub in (s.query(_m.Submission).filter_by(studentId=student_id)
                    .order_by(_m.Submission.id.desc()).limit(6).all()):
            kp = kps.get(q2kp.get(sub.qId, ""))
            acts.append({
                "id": f"A{sub.id}", "type": "practice",
                "title": f"{'答对' if sub.correct else '答错'}「{(kp.name if kp else '知识点练习')}」练习题",
                "meta": f"{sub.duration or 0} 秒 · {'正确' if sub.correct else '错误'}",
                "time": time_ago(sub.ts), "level": "ok" if sub.correct else "warn",
                "_ts": sub.ts,
            })
        for a in open_alerts[:3]:
            acts.append({
                "id": f"AL{a.id}", "type": "alert", "title": a.title,
                "meta": "预警触发 · 待处理", "time": time_ago(a.createdAt),
                "level": "danger" if a.level == "red" else "warn", "_ts": a.createdAt,
            })
        for m in (s.query(_m.Message).filter_by(userId=student_id)
                  .order_by(_m.Message.id.desc()).limit(2).all()):
            acts.append({
                "id": f"M{m.id}", "type": "message", "title": f"教师消息：{m.title}",
                "meta": "来自 " + (m.sender or "教师"), "time": time_ago(m.time),
                "level": "brand", "_ts": m.time,
            })
        acts.sort(key=lambda x: x["_ts"] or "", reverse=True)
        for a in acts:
            a.pop("_ts", None)

        return {
            "overview": overview,
            "coreMetrics": core_metrics,
            "todos": todos[:4],
            "weakPoints": weak_points,
            "suggestedQuestions": suggested,
            "recentActivities": acts[:5],
        }


# ---------------------------------------------------------------- 教师驾驶舱

def _accuracy_between(s, student_ids: list, start: datetime, end: datetime) -> float:
    if not student_ids:
        return 0.0
    rows = (s.query(_m.Submission.correct)
            .filter(_m.Submission.studentId.in_(student_ids)).all())
    vals = []
    for (c,) in rows:
        vals.append(1.0 if c else 0.0)
    return pct(sum(vals), len(vals))


def teacher_dashboard(class_id: str = "CL2301") -> dict:
    with SessionLocal() as s:
        ids = student_ids_of(s, class_id)
        students = s.query(_m.Student).filter(_m.Student.classId == class_id).all() if class_id else s.query(_m.Student).all()
        if not students:
            students = s.query(_m.Student).all()
            ids = [x.userId for x in students]
        cls = s.get(_m.ClassGroup, class_id) if class_id else None
        kps = kp_index(s)

        n = len(students)
        avg_completion = round1(sum(x.completionRate for x in students) / n) if n else 0.0
        avg_mastery = round1(sum(x.masteryRate for x in students) / n) if n else 0.0
        avg_goal = round1(sum(x.goalAchieveRate for x in students) / n) if n else 0.0

        open_alerts = s.query(_m.Alert).filter_by(status="open").all()
        alert_ids = {a.studentId for a in open_alerts if a.studentId in set(ids)}
        today = today_str()
        active_today = (s.query(func.count(_m.StudyDay.id))
                        .filter(_m.StudyDay.studentId.in_(ids), _m.StudyDay.day == today).scalar() or 0) if ids else 0
        submit_today = (s.query(func.count(_m.Submission.id)).filter(_m.Submission.studentId.in_(ids)).scalar() or 0) if ids else 0

        # 环比：近 7 日 vs 前 7 日正确率（掌握率变化）；完成率用「新覆盖知识点数」近似
        now = datetime.now(timezone.utc)
        d7 = now - timedelta(days=7)
        d14 = now - timedelta(days=14)
        subs = s.query(_m.Submission).filter(_m.Submission.studentId.in_(ids)).all() if ids else []
        q2kp = {q.qId: q.kpId for q in s.query(_m.Question.qId, _m.Question.kpId).all()}
        recent, prev = [], []
        kp_recent, kp_prev = set(), set()
        for sub in subs:
            dt = parse_ts(sub.ts)
            if not dt:
                continue
            if dt >= d7:
                recent.append(1.0 if sub.correct else 0.0)
                kp_recent.add(q2kp.get(sub.qId, ""))
            elif dt >= d14:
                prev.append(1.0 if sub.correct else 0.0)
                kp_prev.add(q2kp.get(sub.qId, ""))
        acc_recent = pct(sum(recent), len(recent))
        acc_prev = pct(sum(prev), len(prev))
        delta_mastery = round1(acc_recent - acc_prev)
        total_kp = max(1, len(kps))
        delta_completion = round1((len(kp_recent) - len(kp_prev)) / total_kp * 100)
        delta_goal = round1(delta_mastery * 0.7 + delta_completion * 0.3)

        class_overview = {
            "classId": class_id or "CL2301",
            "className": (cls.name if cls else (students[0].className if students else "")),
            "studentCount": n,
            "avgCompletionRate": avg_completion,
            "avgMasteryRate": avg_mastery,
            "avgGoalAchieve": avg_goal,
            "alertStudentCount": len(alert_ids),
            "alertRatio": pct(len(alert_ids), n),
            "activeToday": active_today,
            "submitToday": submit_today,
            "deltaCompletion": delta_completion,
            "deltaMastery": delta_mastery,
            "deltaGoal": delta_goal,
            "updatedAt": now_str(),
        }

        # ---- 实时动态
        feed, idx = [], 1
        name_of = {x.userId: x.name for x in students}
        for sub in (s.query(_m.Submission).filter(_m.Submission.studentId.in_(ids))
                    .order_by(_m.Submission.id.desc()).limit(4).all()) if ids else []:
            kp = kps.get(q2kp.get(sub.qId, ""))
            feed.append({
                "id": f"F{idx}", "type": "submit",
                "text": f"{name_of.get(sub.studentId, sub.studentId)} 作答了「{(kp.name if kp else '练习题')}」",
                "meta": f"{'正确' if sub.correct else '错误'} · 用时 {max(1, (sub.duration or 30) // 60)} 分钟",
                "time": time_ago(sub.ts), "level": "ok" if sub.correct else "warn",
                "_ts": sub.ts,
            })
            idx += 1
        for a in (s.query(_m.Alert).filter(_m.Alert.studentId.in_(ids))
                  .order_by(_m.Alert.id.desc()).limit(4).all()) if ids else []:
            feed.append({
                "id": f"F{idx}", "type": "alert",
                "text": f"预警：{name_of.get(a.studentId, a.studentId)} · {a.title}",
                "meta": (a.trigger or "规则触发")[:24], "time": time_ago(a.createdAt),
                "level": "danger" if a.level == "red" else "warn", "_ts": a.createdAt,
            })
            idx += 1
        feed.sort(key=lambda x: x["_ts"] or "", reverse=True)
        for f in feed:
            f.pop("_ts", None)

        # ---- 待办
        pending_iv = s.query(func.count(_m.InterventionPlan.id)).filter_by(status="pending").scalar() or 0
        # Question 的主键是业务主键 qId，没有自增 id 列
        pending_q = s.query(func.count(_m.Question.qId)).filter_by(status="pending").scalar() or 0
        weak_rank = _weak_kps(s, ids, limit=1)
        todos = [{
            "id": "TT1", "level": "danger" if len(open_alerts) else "ok",
            "title": f"{len(open_alerts)} 条预警待处理",
            "desc": f"其中红色 {sum(1 for a in open_alerts if a.level == 'red')} 条、"
                    f"黄色 {sum(1 for a in open_alerts if a.level == 'yellow')} 条",
            "action": "去处理", "target": "alerts",
        }, {
            "id": "TT2", "level": "brand" if pending_iv else "ok",
            "title": f"{pending_iv} 条干预建议待确认",
            "desc": "来自共性薄弱点归因，确认后自动推送资源与练习",
            "action": "去确认", "target": "intervention",
        }]
        if pending_q:
            todos.append({
                "id": "TT3", "level": "warn", "title": f"{pending_q} 道习题待审核",
                "desc": "AI 生成或批量导入的题目需审核后发布", "action": "去审核", "target": "question",
            })
        todos.append({
            "id": "TT4", "level": "ok",
            "title": f"「{weak_rank[0]['name'] if weak_rank else '本章'}」阶段性学情报告可生成",
            "desc": f"数据已覆盖 {len(kps)} 个知识点、{n} 名学生", "action": "生成报告", "target": "report",
        })

        return {
            "classOverview": class_overview,
            "liveFeed": feed[:6],
            "todos": todos[:4],
            "kpRanking": _weak_kps(s, ids, limit=5),
        }


def _weak_kps(s, student_ids: list, limit: int = 5) -> list:
    """班级掌握率最低的 N 个知识点。"""
    avg = class_kp_mastery(s, student_ids)
    if not avg:
        return []
    kps = kp_index(s)
    low = {r.kpId for r in s.query(_m.MasteryRecord).filter(
        _m.MasteryRecord.studentId.in_(student_ids),
        _m.MasteryRecord.mastery < 60).all()} if student_ids else set()
    rows = sorted(avg.items(), key=lambda kv: kv[1])[:limit]
    out = []
    for kp_id, val in rows:
        kp = kps.get(kp_id)
        out.append({
            "kpId": kp_id, "name": kp.name if kp else kp_id,
            "mastery": round1(val),
            "students": len(student_ids),
            "weakCount": sum(1 for r in s.query(_m.MasteryRecord).filter_by(kpId=kp_id)
                             .all() if r.studentId in set(student_ids) and r.mastery < 60),
        })
    return out
