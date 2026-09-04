"""真实数据访问层（Repository）。

职责
----
- **实体级读写**：题目、作答、预警、干预、消息、资源等表的增删改查。
- **学情聚合**：掌握矩阵、能力雷达、成长轨迹、班级对比、热力图、个体画像等
  （跨表聚合但属于单学生/单班级维度，仍放 repo；跨模块的驾驶舱/图谱/归因/报告放 services）。
- 返回**前端契约形状**：字段名与 `mock_data.json` 逐层一致，`api.js` 切到 http 后零改页面。

约定
----
- 所有函数都不依赖 FastAPI（可单独在脚本里调用）。
- 写操作（练习判分、预警复核、干预、题库编辑）直接落表并 commit。
"""
import json
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone

from .core.envelope import BizError  # noqa: F401  便于 repo 层抛业务异常
from .db import models as _m
from .db.session import SessionLocal
from .services.common import kp_index, level_of, parse_ts, pct, round1, student_ids_of, time_ago

# ---------------------------------------------------------------- 常量

_TYPE_CN = {"choice": "单选题", "single": "单选题", "multi": "多选题", "judge": "判断题",
            "blank": "填空题", "code": "算法设计题"}

# 能力雷达六个维度 → 关联知识点（与前端 abilityRadar.indicators 顺序一致）
ABILITY_DIMS = [
    ("线性结构运用", ["KP11", "KP12", "KP13", "KP14"]),
    ("树形结构构建", ["KP31", "KP32", "KP33", "KP34", "KP44"]),
    ("图结构与算法", ["KP41", "KP42", "KP43", "KP51", "KP52", "KP53"]),
    ("复杂度分析", ["KP01", "KP02"]),
    ("算法设计与实现", ["KP61", "KP62", "KP63", "KP64", "KP71", "KP72", "KP73"]),
    ("工程问题建模", ["KP21", "KP22", "KP23", "KP24"]),
]
_GOAL_BASELINE = [80, 80, 80, 80, 75, 75]

# 学习时段分布（与前端 studyTimeDist.xAxis 一致）
_TIME_BUCKETS = [("00-06", 0, 6), ("06-09", 6, 9), ("09-12", 9, 12), ("12-15", 12, 15),
                 ("15-18", 15, 18), ("18-21", 18, 21), ("21-24", 21, 24)]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def _type_cn(t: str) -> str:
    return _TYPE_CN.get((t or "").lower(), t or "单选题")


def _kp_name(s, kp_id: str) -> str:
    kp = s.get(_m.KnowledgePoint, kp_id) if kp_id else None
    return kp.name if kp else (kp_id or "")


def _kp_path(s, kp) -> list:
    """kpPath = 前置 + 自身 + 后置（名称数组）。"""
    if not kp:
        return []
    names = [_kp_name(s, k) for k in json.loads(kp.preKp or "[]")]
    names.append(kp.name)
    names += [_kp_name(s, k) for k in json.loads(kp.postKp or "[]")]
    return [n for n in names if n]


def _mastery_of(s, student_id: str) -> dict:
    return {r.kpId: r.mastery for r in s.query(_m.MasteryRecord).filter_by(studentId=student_id).all()}


# ---------------------------------------------------------------- 课程 / 知识点

def get_course(course_id: str) -> dict:
    with SessionLocal() as s:
        c = s.get(_m.Course, course_id)
        if not c:
            return {}
        kp_n = s.query(_m.KnowledgePoint).count()
        chapters = len({k.chapter for k in s.query(_m.KnowledgePoint).all() if k.chapter})
        return {
            "courseId": c.courseId, "name": c.name, "code": c.code, "term": c.term,
            "teacher": c.teacherId, "credit": c.credit, "chapters": chapters,
            "knowledgePoints": kp_n, "resources": s.query(_m.Resource).count(),
            "questions": s.query(_m.Question).count(),
        }


def get_kp_detail(kp_id: str, student_id: str = "", class_id: str = "") -> dict:
    """知识点详情（结构 + 真实掌握 + 资源 + 题目统计）。"""
    from .services.graph import kp_detail as _svc_kp_detail
    return _svc_kp_detail(kp_id, student_id=student_id, class_id=class_id)


# ---------------------------------------------------------------- 题目库

def list_questions(kp_id="", type="", status="", difficulty="", keyword="",
                   page=1, size=20) -> dict:
    with SessionLocal() as s:
        q = s.query(_m.Question)
        if kp_id:
            q = q.filter(_m.Question.kpId == kp_id)
        if type:
            q = q.filter(_m.Question.type == type)
        if status:
            q = q.filter(_m.Question.status == status)
        if difficulty:
            q = q.filter(_m.Question.difficulty == int(difficulty))
        if keyword:
            q = q.filter(_m.Question.stem.contains(keyword))
        total = q.count()
        rows = q.order_by(_m.Question.qId).offset((page - 1) * size).limit(size).all()

        # 一次取出本题页所有作答，避免 N+1
        qids = [r.qId for r in rows]
        subs = s.query(_m.Submission).filter(_m.Submission.qId.in_(qids)).all() if qids else []
        rate = {}
        for x in subs:
            ok, n = rate.get(x.qId, (0, 0))
            rate[x.qId] = (ok + (1 if x.correct else 0), n + 1)

        items = [{
            "qId": r.qId, "stem": r.stem, "type": _type_cn(r.type),
            "kp": _kp_name(s, r.kpId), "difficulty": r.difficulty, "isKey": r.isKey,
            "useCount": r.useCount or 0,
            "correctRate": round(rate.get(r.qId, (0, 0))[0] / rate[r.qId][1] * 100) if r.qId in rate else 0,
            "status": r.status, "source": r.source, "createdAt": r.createdAt,
        } for r in rows]
    return {"total": total, "list": items, "page": page, "size": size}


def get_question(q_id: str) -> dict:
    with SessionLocal() as s:
        r = s.get(_m.Question, q_id)
        if not r:
            return {}
        return {"qId": r.qId, "kpId": r.kpId, "type": r.type, "stem": r.stem,
                "options": json.loads(r.options_json or "[]"), "answer": r.answer,
                "analysis": r.analysis, "difficulty": r.difficulty,
                "source": r.source, "status": r.status}


def upsert_question(p: dict) -> dict:
    qid = p.get("qId") or ("Q" + uuid.uuid4().hex[:8])
    with SessionLocal() as s:
        r = s.get(_m.Question, qid)
        if r is None:
            r = _m.Question(qId=qid, createdAt=_now())
            s.add(r)
        r.kpId = p.get("kpId", r.kpId)
        r.type = p.get("type", r.type or "choice")
        r.stem = p.get("stem", r.stem)
        r.options_json = json.dumps(p.get("options", json.loads(r.options_json or "[]")), ensure_ascii=False)
        r.answer = str(p.get("answer", r.answer))
        r.analysis = p.get("analysis", r.analysis or "")
        r.difficulty = int(p.get("difficulty", r.difficulty or 1) or 1)
        r.source = p.get("source", r.source)
        r.status = p.get("status", r.status or "pending")
        r.isKey = bool(p.get("isKey", r.isKey))
        s.commit()
        return {"qId": qid, "updated": True}


def delete_question(q_id: str) -> dict:
    with SessionLocal() as s:
        r = s.get(_m.Question, q_id)
        if r:
            s.delete(r)
            s.commit()
    return {"qId": q_id, "removed": True}


def import_questions(items: list) -> dict:
    total, ok = len(items), 0
    with SessionLocal() as s:
        for p in items:
            qid = p.get("qId") or ("Q" + uuid.uuid4().hex[:8])
            r = s.get(_m.Question, qid)
            if r is None:
                r = _m.Question(qId=qid)
                s.add(r)
            r.kpId = p.get("kpId", "")
            r.type = p.get("type", "choice")
            r.stem = p.get("stem", "")
            r.options_json = json.dumps(p.get("options", []), ensure_ascii=False)
            r.answer = str(p.get("answer", ""))
            r.analysis = p.get("analysis", "")
            r.difficulty = int(p.get("difficulty", 1) or 1)
            r.source = p.get("source", "")
            r.status = p.get("status", "pending")
            r.createdAt = r.createdAt or _now()
            ok += 1
        s.commit()
    return {"taskId": "IMP" + uuid.uuid4().hex[:8], "total": total,
            "success": ok, "failed": total - ok}


# ---------------------------------------------------------------- 练习闭环

def _pick_questions(mode: str, kp_ids: list, count: int, student_id: str) -> list:
    with SessionLocal() as s:
        q = s.query(_m.Question).filter(_m.Question.answer != "")
        if kp_ids:
            q = q.filter(_m.Question.kpId.in_(kp_ids))
        if mode == "weak":
            low = [m.kpId for m in s.query(_m.MasteryRecord)
                   .filter(_m.MasteryRecord.studentId == student_id,
                           _m.MasteryRecord.mastery < 70).all()]
            if low:
                q = q.filter(_m.Question.kpId.in_(low))
        elif mode == "wrong":
            wrong_ids = [x.qId for x in s.query(_m.Submission)
                         .filter_by(studentId=student_id, correct=False, mastered=False).all()]
            if wrong_ids:
                q = q.filter(_m.Question.qId.in_(wrong_ids))
        return [r.qId for r in q.limit(count).all()]


def create_practice_session(student_id: str, mode: str, kp_ids: list, count: int, difficulty: int) -> dict:
    qids = _pick_questions(mode, kp_ids or [], count or 10, student_id)
    sid = "PS" + uuid.uuid4().hex[:10]
    with SessionLocal() as s:
        s.add(_m.PracticeSession(
            sessionId=sid, studentId=student_id, mode=mode or "random",
            kpIds_json=json.dumps(kp_ids or [], ensure_ascii=False),
            qIds_json=json.dumps(qids, ensure_ascii=False),
            count=len(qids), status="open", ts=_now(),
        ))
        s.commit()
    return {"sessionId": sid, "count": len(qids), "qIds": qids}


def latest_session_id(student_id: str) -> str | None:
    with SessionLocal() as s:
        ps = (s.query(_m.PracticeSession).filter_by(studentId=student_id)
              .order_by(_m.PracticeSession.id.desc()).first())
        return ps.sessionId if ps else None


def get_session_questions(session_id: str) -> list:
    with SessionLocal() as s:
        ps = s.query(_m.PracticeSession).filter_by(sessionId=session_id).first()
        if not ps:
            return []
        qids = json.loads(ps.qIds_json or "[]")
        rows = s.query(_m.Question).filter(_m.Question.qId.in_(qids)).all()
        by_id = {r.qId: r for r in rows}
        out = []
        for qid in qids:
            r = by_id.get(qid)
            if not r:
                continue
            kp = s.get(_m.KnowledgePoint, r.kpId) if r.kpId else None
            out.append({
                "qId": r.qId, "kpId": r.kpId, "type": r.type, "stem": r.stem,
                "options": json.loads(r.options_json or "[]"), "difficulty": r.difficulty,
                "score": 100 // max(1, len(qids)), "answer": r.answer, "analysis": r.analysis,
                "kpPath": _kp_path(s, kp), "preKp": json.loads(kp.preKp or "[]") if kp else [],
                "isKey": r.isKey, "classCorrectRate": _question_correct_rate(s, r.qId),
                "avgSeconds": 0, "errorType": "",
            })
    return out


def _question_correct_rate(s, q_id: str) -> int:
    subs = s.query(_m.Submission).filter_by(qId=q_id).all()
    if not subs:
        return 0
    return round(sum(1 for x in subs if x.correct) / len(subs) * 100)


def submit_answer(student_id: str, session_id: str, q_id: str, answer, duration: int = 0) -> dict:
    """判分 → 掌握度 EMA 更新 → 低掌握度自动预警。"""
    with SessionLocal() as s:
        q = s.get(_m.Question, q_id)
        if not q:
            raise BizError(404, "题目不存在")
        correct = str(answer).strip().upper() == str(q.answer).strip().upper()
        kp_id = q.kpId or ""
        rec = (s.query(_m.MasteryRecord).filter_by(studentId=student_id, kpId=kp_id).first()
               if kp_id else None)
        prev = rec.mastery if rec else 70.0
        new_mastery = round(prev * 0.7 + (100.0 if correct else 0.0) * 0.3, 1)

        s.add(_m.Submission(studentId=student_id, qId=q_id, answer=str(answer),
                            correct=correct, score=100.0 if correct else 0.0,
                            ts=_now(), duration=int(duration or 0),
                            errorType="" if correct else (q.analysis and "概念混淆" or "概念混淆")))
        s.flush()
        if kp_id:
            if rec:
                rec.mastery = new_mastery
                rec.correctRate = new_mastery
                rec.completion = min(100.0, (rec.completion or 0) + 5.0)
            else:
                s.add(_m.MasteryRecord(studentId=student_id, kpId=kp_id, mastery=new_mastery,
                                       correctRate=new_mastery, completion=20.0, status=""))
            if new_mastery < 60:
                exist = (s.query(_m.Alert).filter_by(studentId=student_id, type="mastery_low",
                                                     kpId=kp_id, status="open").first())
                if not exist:
                    kp_name = _kp_name(s, kp_id)
                    s.add(_m.Alert(
                        alertId="AL" + uuid.uuid4().hex[:10].upper(),
                        studentId=student_id, studentName=_student_name(s, student_id),
                        type="mastery_low", level="red" if new_mastery < 50 else "yellow",
                        title=f"「{kp_name}」掌握率偏低",
                        desc=f"当前掌握率 {round(new_mastery)}%，低于课程达标线 60%。",
                        trigger="规则 R-M02：核心知识点掌握率 < 60%",
                        kpId=kp_id, kp=kp_name,
                        detail_json=json.dumps({"current": round(new_mastery), "threshold": 60,
                                                "classAvg": round(_class_avg(s, kp_id)),
                                                "errorCount": _wrong_count(s, student_id, kp_id),
                                                "relatedQuestions": s.query(_m.Question)
                                                .filter_by(kpId=kp_id).count()}, ensure_ascii=False),
                        suggestions_json=json.dumps(_suggestions(s, kp_id), ensure_ascii=False),
                        trend_json="[]", createdAt=_now(), status="open", read=False,
                    ))
        # 学习日历同步累加（驾驶舱贡献图）
        _touch_study_day(s, student_id, int(duration or 0))
        s.commit()

        kp = s.get(_m.KnowledgePoint, kp_id) if kp_id else None
        class_rate = int(_kp_correct_rate(s, kp_id)) if kp_id else 0
        return {
            "qId": q_id, "correct": correct, "rightAnswer": q.answer,
            "analysis": q.analysis or ("回答正确，继续保持。" if correct else "回答有误，建议复习相关知识点后重做。"),
            "kpPath": _kp_path(s, kp) if kp else [kp_id],
            "classCorrectRate": class_rate, "avgSeconds": int(duration or 0),
            "masteryDelta": round1(new_mastery - prev), "errorType": (None if correct else "概念混淆"),
        }


def _student_name(s, student_id: str) -> str:
    st = s.get(_m.Student, student_id)
    return st.name if st else student_id


def _class_avg(s, kp_id: str) -> float:
    rows = s.query(_m.MasteryRecord).filter_by(kpId=kp_id).all()
    return round1(sum(r.mastery for r in rows) / len(rows)) if rows else 0.0


def _wrong_count(s, student_id: str, kp_id: str) -> int:
    return (s.query(_m.Submission).join(_m.Question, _m.Submission.qId == _m.Question.qId)
            .filter(_m.Submission.studentId == student_id, _m.Question.kpId == kp_id,
                    _m.Submission.correct.is_(False)).count())


def _kp_correct_rate(s, kp_id: str) -> float:
    subs = (s.query(_m.Submission).join(_m.Question, _m.Submission.qId == _m.Question.qId)
            .filter(_m.Question.kpId == kp_id).all())
    return pct(sum(1 for x in subs if x.correct), len(subs))


def _suggestions(s, kp_id: str) -> list:
    """按知识点生成改进建议（AI 暂缓期间用规则推荐资源 + 复习 + 练习）。"""
    kp_name = _kp_name(s, kp_id)
    pre = json.loads((s.get(_m.KnowledgePoint, kp_id).preKp if s.get(_m.KnowledgePoint, kp_id) else "[]") or "[]")
    res = s.query(_m.Resource).filter_by(kpId=kp_id).first()
    out = []
    if res:
        out.append({"type": "video", "text": f"观看补救微课《{res.title}》", "resId": res.resId})
    if pre:
        out.append({"type": "review", "text": f"回顾前置知识点「{_kp_name(s, pre[0])}」", "kpId": pre[0]})
    out.append({"type": "practice", "text": f"完成「{kp_name}」靶向练习 6 题", "packId": "PK" + kp_id})
    out.append({"type": "ai", "text": f"向 AI 助教提问：{kp_name} 的核心思路是什么"})
    return out


def _touch_study_day(s, student_id: str, seconds: int) -> None:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = s.query(_m.StudyDay).filter_by(studentId=student_id, day=day).first()
    if row is None:
        s.add(_m.StudyDay(studentId=student_id, day=day, minutes=max(1, seconds // 60), questions=1))
    else:
        row.minutes = int(row.minutes or 0) + max(1, seconds // 60)
        row.questions = int(row.questions or 0) + 1


def finish_session(session_id: str) -> dict:
    with SessionLocal() as s:
        ps = s.query(_m.PracticeSession).filter_by(sessionId=session_id).first()
        if not ps:
            return {}
        qids = json.loads(ps.qIds_json or "[]")
        subs = (s.query(_m.Submission).filter(_m.Submission.studentId == ps.studentId,
                                              _m.Submission.qId.in_(qids))
                .order_by(_m.Submission.id.desc()).limit(len(qids)).all())
        q_kp = {q.qId: q.kpId for q in s.query(_m.Question).filter(_m.Question.qId.in_(qids)).all()}
        total, correct = len(subs), sum(1 for x in subs if x.correct)
        wrong = total - correct

        kp_set = []
        for x in subs:
            k = q_kp.get(x.qId)
            if k and k not in kp_set:
                kp_set.append(k)
        kp_changes, score_gain = [], 0.0
        for kp_id in kp_set:
            rec = s.query(_m.MasteryRecord).filter_by(studentId=ps.studentId, kpId=kp_id).first()
            after = rec.mastery if rec else 70.0
            kp_subs = [x for x in subs if q_kp.get(x.qId) == kp_id]
            c = sum(1 for x in kp_subs if x.correct)
            w = len(kp_subs) - c
            delta = round1(c * 2.1 - w * 1.4)
            kp = s.get(_m.KnowledgePoint, kp_id)
            kp_changes.append({"kpId": kp_id, "name": kp.name if kp else kp_id,
                               "before": round1(max(0.0, after - delta)), "after": round1(after),
                               "delta": delta})
            score_gain += delta

        error_types = []
        if wrong:
            cnt = Counter("概念混淆" if (x.duration or 0) >= 30 else "计算失误"
                          for x in subs if not x.correct)
            error_types = [{"type": k, "count": v} for k, v in cnt.most_common()]

        st = s.get(_m.Student, ps.studentId)
        cls = st.classId if st else "CL2301"
        peers = [p.userId for p in s.query(_m.Student).filter_by(classId=cls).all()]
        peer_recs = (s.query(_m.MasteryRecord).filter(_m.MasteryRecord.studentId.in_(peers)).all()
                     if peers else [])
        class_accuracy = round1(sum(r.mastery for r in peer_recs) / len(peer_recs)) if peer_recs else 0.0
        duration_seconds = sum(x.duration or 0 for x in subs)
        ps.status = "done"
        s.commit()

        weakest = sorted(kp_changes, key=lambda k: k["after"])[:3]
        return {
            "reportId": "RP" + session_id[2:], "mode": ps.mode,
            "total": total, "correct": correct, "wrong": wrong,
            "accuracy": pct(correct, total), "durationSeconds": duration_seconds,
            "avgSeconds": round1(duration_seconds / total) if total else 0.0,
            "classAccuracy": class_accuracy, "scoreGain": round1(score_gain),
            "kpChanges": kp_changes, "errorTypes": error_types,
            "nextSuggestion": ("建议优先巩固：" + "、".join(k["name"] for k in weakest) + "。")
            if weakest else "继续保持，可尝试更高难度的练习。",
        }


def wrong_book(student_id: str, mastered=None, error_type: str = "", page: int = 1, size: int = 20) -> dict:
    with SessionLocal() as s:
        subs = s.query(_m.Submission).filter_by(studentId=student_id, correct=False).all()
        latest = {}
        for x in subs:
            if x.qId not in latest or x.id > latest[x.qId].id:
                latest[x.qId] = x
        items = []
        for qid, last in latest.items():
            if mastered is not None and last.mastered != mastered:
                continue
            qq = s.get(_m.Question, qid)
            kp_id = qq.kpId if qq else ""
            items.append({
                "qId": qid, "stem": qq.stem if qq else "", "type": _type_cn(qq.type) if qq else "",
                "myAnswer": last.answer, "answer": qq.answer if qq else "",
                "wrongCount": sum(1 for x in subs if x.qId == qid),
                "errorType": last.errorType or "概念混淆",
                "kp": _kp_name(s, kp_id), "kpId": kp_id,
                "difficulty": qq.difficulty if qq else 0,
                "lastTime": last.ts, "mastered": last.mastered,
            })
        items.sort(key=lambda x: x["lastTime"], reverse=True)
        total = len(items)
    return {"total": total, "list": items[(page - 1) * size: (page - 1) * size + size],
            "page": page, "size": size}


def get_wrong_detail(student_id: str, q_id: str) -> dict:
    with SessionLocal() as s:
        qq = s.get(_m.Question, q_id)
        if not qq:
            return {}
        kp = s.get(_m.KnowledgePoint, qq.kpId) if qq.kpId else None
        subs = (s.query(_m.Submission).filter_by(studentId=student_id, qId=q_id)
                .order_by(_m.Submission.id.desc()).all())
        history = [{"time": x.ts, "answer": x.answer, "correct": x.correct} for x in subs]
        similar = [{"qId": r.qId, "kp": _kp_name(s, r.kpId), "stem": r.stem}
                   for r in s.query(_m.Question).filter(_m.Question.kpId == qq.kpId,
                                                        _m.Question.qId != q_id).limit(3).all()]
        resources = [{"type": r.type, "name": r.title,
                      "meta": (r.duration or (f"{r.pages} 页" if r.pages else ""))}
                     for r in s.query(_m.Resource).filter_by(kpId=qq.kpId).limit(4).all()]
        return {
            "qId": q_id, "type": _type_cn(qq.type), "difficulty": qq.difficulty,
            "score": 100, "stem": qq.stem, "options": json.loads(qq.options_json or "[]"),
            "answer": qq.answer, "analysis": qq.analysis or "建议结合教材与课件复习该知识点。",
            "kpPath": _kp_path(s, kp) if kp else [qq.kpId], "kpId": qq.kpId,
            "preKp": json.loads(kp.preKp or "[]") if kp else [],
            "isKey": qq.isKey, "classCorrectRate": _question_correct_rate(s, q_id),
            "avgSeconds": round(sum(x.duration or 0 for x in subs) / len(subs)) if subs else 0,
            "errorType": (subs[0].errorType if subs and subs[0].errorType else "概念混淆"),
            "history": history, "similar": similar, "resources": resources,
            "tips": "可将该题标记已掌握后移出错题本，或加入错题重练计划。",
        }


def delete_wrong(student_id: str, q_id: str) -> dict:
    with SessionLocal() as s:
        s.query(_m.Submission).filter_by(studentId=student_id, qId=q_id).update({"mastered": True})
        s.commit()
    return {"qId": q_id, "removed": True}


# ---------------------------------------------------------------- 学生学情

def mastery_matrix(student_id: str) -> list:
    """按章节分组的掌握矩阵（章节完成率/掌握率 + 每个知识点的题量与正确数）。"""
    with SessionLocal() as s:
        kps = kp_index(s)
        recs = {r.kpId: r for r in s.query(_m.MasteryRecord).filter_by(studentId=student_id).all()}
        q2kp = {q.qId: q.kpId for q in s.query(_m.Question.qId, _m.Question.kpId).all()}
        stat = {}
        for x in s.query(_m.Submission).filter_by(studentId=student_id).all():
            kp = q2kp.get(x.qId, "")
            st = stat.setdefault(kp, {"questions": 0, "correct": 0})
            st["questions"] += 1
            st["correct"] += 1 if x.correct else 0

        groups = {}
        for kp in sorted(kps.values(), key=lambda k: (k.orderNo, k.kpId)):
            key = kp.chapterName or (f"第{kp.chapter}章" if kp.chapter else "其他")
            groups.setdefault(key, []).append(kp)
        out = []
        for chapter, items_kp in groups.items():
            items = []
            for kp in items_kp:
                rec = recs.get(kp.kpId)
                m = round1(rec.mastery if rec else 0)
                st = stat.get(kp.kpId, {"questions": 0, "correct": 0})
                items.append({"kpId": kp.kpId, "name": kp.name,
                              "completion": round(rec.completion if rec else 0),
                              "mastery": round(m), "level": level_of(m),
                              "questions": st["questions"], "correct": st["correct"],
                              "isKey": kp.isKey})
            out.append({
                "chapter": chapter,
                "completionRate": round(sum(i["completion"] for i in items) / len(items)) if items else 0,
                "masteryRate": round(sum(i["mastery"] for i in items) / len(items)) if items else 0,
                "items": items,
            })
    return out


def ability_radar(student_id: str) -> dict:
    with SessionLocal() as s:
        mine = _mastery_of(s, student_id)
        st = s.get(_m.Student, student_id)
        peers = [p.userId for p in s.query(_m.Student)
                 .filter_by(classId=st.classId if st else "CL2301").all()]
        peer_rows = (s.query(_m.MasteryRecord).filter(_m.MasteryRecord.studentId.in_(peers)).all()
                     if peers else [])
        peer_avg = {}
        for r in peer_rows:
            acc = peer_avg.setdefault(r.kpId, [])
            acc.append(r.mastery)
        peer_avg = {k: sum(v) / len(v) for k, v in peer_avg.items()}

        my_data, class_data = [], []
        for _, kp_ids in ABILITY_DIMS:
            mv = [mine[k] for k in kp_ids if k in mine]
            cv = [peer_avg[k] for k in kp_ids if k in peer_avg]
            my_data.append(round1(sum(mv) / len(mv)) if mv else 0)
            class_data.append(round1(sum(cv) / len(cv)) if cv else 0)
    return {
        "indicators": [{"name": n, "max": 100} for n, _ in ABILITY_DIMS],
        "series": [{"name": "我的达成度", "data": my_data},
                   {"name": "班级平均", "data": class_data},
                   {"name": "目标基线", "data": _GOAL_BASELINE}],
    }


def growth_track(student_id: str, dimension: str = "week") -> dict:
    """成长轨迹：按周累计「完成率 / 掌握率 / 目标达成度」三条曲线。"""
    weeks = 8
    with SessionLocal() as s:
        kps = kp_index(s)
        total_kp = max(1, len(kps))
        st = s.get(_m.Student, student_id)
        ratio = (st.goalAchieveRate / st.masteryRate) if (st and st.masteryRate) else 0.92
        q2kp = {q.qId: q.kpId for q in s.query(_m.Question.qId, _m.Question.kpId).all()}
        subs = [x for x in s.query(_m.Submission).filter_by(studentId=student_id).all()
                if parse_ts(x.ts)]
        subs.sort(key=lambda x: parse_ts(x.ts))
        end = datetime.now(timezone.utc)

        x_axis, completion, mastery, goal = [], [], [], []
        for i in range(weeks):
            x_axis.append(f"第{i + 1}周")
            cutoff = end - timedelta(days=7 * (weeks - 1 - i))
            done = [x for x in subs if parse_ts(x.ts) <= cutoff]
            kp_set = {q2kp.get(x.qId, "") for x in done if q2kp.get(x.qId)}
            completion.append(round(len(kp_set) / total_kp * 100))
            acc = pct(sum(1 for x in done if x.correct), len(done))
            mastery.append(acc)
            goal.append(round1(acc * ratio))

        # 里程碑 = 真实事件落在哪一周：达标 / 覆盖 / 触发预警。
        # 之前只按「累计掌握率过 60/75」生成，一旦整体正确率不到阈值就返回空数组。
        alerts = s.query(_m.Alert).filter_by(studentId=student_id).all()
        cand: list[tuple[int, int, str]] = []   # (优先级, 周下标, 文案)

        def first_hit(curve, threshold, tpl, prio):
            for i, v in enumerate(curve):
                if v >= threshold:
                    cand.append((prio, i, tpl.format(v=round(v))))
                    return

        first_hit(mastery, 60, "累计掌握率首次达到 {v}%", 0)
        first_hit(completion, 60, "知识点覆盖首次达到 {v}%", 1)
        for al in alerts:
            dt = parse_ts(al.createdAt)
            if not dt:
                continue
            for i in range(weeks):
                start = end - timedelta(days=7 * (weeks - i))
                if start <= dt < start + timedelta(days=7):
                    cand.append((2, i, f"触发「{al.title or al.type}」"))
                    break

        cand.sort(key=lambda x: (x[1], x[0]))
        milestones, used_week = [], set()
        for _, i, text in cand:
            if i in used_week:
                continue
            used_week.add(i)
            milestones.append({"x": x_axis[i], "label": text})
            if len(milestones) >= 2:
                break
        if not milestones:                       # 兜底：标注掌握率最高的那一周
            peak = max(range(weeks), key=lambda i: mastery[i])
            milestones.append({"x": x_axis[peak], "label": f"掌握率阶段峰值 {round(mastery[peak])}%"})
        return {"dimension": dimension, "xAxis": x_axis,
                "series": [
                    {"name": "知识点完成率", "data": completion, "color": "#6366f1"},
                    {"name": "掌握率", "data": mastery, "color": "#22c55e"},
                    {"name": "能力目标达成度", "data": goal, "color": "#8b5cf6"},
                ],
                "milestones": milestones}


def class_compare(student_id: str) -> dict:
    """我与班级的对比：5 项指标的 mine / classAvg / classBest / diff。"""
    with SessionLocal() as s:
        me = s.get(_m.Student, student_id)
        peers = s.query(_m.Student).filter_by(classId=me.classId if me else "CL2301").all()
        if not peers:
            peers = s.query(_m.Student).all()
        n = len(peers) or 1
        kps = kp_index(s)
        q2kp = {q.qId: q.kpId for q in s.query(_m.Question.qId, _m.Question.kpId).all()}

        def acc_of(uid):
            subs = s.query(_m.Submission).filter_by(studentId=uid).all()
            return pct(sum(1 for x in subs if x.correct), len(subs))

        def cover_of(uid):
            ks = {q2kp.get(x.qId, "") for x in s.query(_m.Submission).filter_by(studentId=uid).all()}
            ks.discard("")
            return pct(len(ks), max(1, len(kps)))

        mine_acc = acc_of(student_id)
        rows = []
        for uid in [p.userId for p in peers]:
            rows.append((uid, cover_of(uid), acc_of(uid)))
        peers_acc = [r[2] for r in rows]
        peers_cover = [r[1] for r in rows]
        mine_cover = cover_of(student_id)
        mine_goal = me.goalAchieveRate if me else 0.0
        peers_goal = [p.goalAchieveRate for p in peers]
        mine_min = int(me.studyMinutes) if me else 0
        peers_min = [int(p.studyMinutes) for p in peers]

        metrics = [
            ("知识点完成率", mine_cover, sum(peers_cover) / n, max(peers_cover or [0])),
            ("知识点掌握率", float(me.masteryRate) if me else 0.0,
             sum(p.masteryRate for p in peers) / n, max(p.masteryRate for p in peers)),
            ("能力目标达成度", mine_goal, sum(peers_goal) / n, max(peers_goal or [0])),
            ("练习正确率", mine_acc, sum(peers_acc) / n, max(peers_acc or [0])),
            ("周均学习时长(分钟)", float(mine_min), sum(peers_min) / n, max(peers_min or [0])),
        ]
        items = [{"metric": name, "mine": round1(mine), "classAvg": round1(avg),
                  "classBest": round(best), "diff": round1(mine - avg)}
                 for name, mine, avg, best in metrics]

        rank = sorted(peers, key=lambda p: -p.masteryRate)
        my_rank = next((i + 1 for i, p in enumerate(rank) if p.userId == student_id), n)
        return {"myRank": my_rank, "totalStudents": n,
                "percentile": round((1 - (my_rank - 1) / n) * 100), "items": items}


# ---------------------------------------------------------------- 预警 / 消息

def student_alerts(student_id: str, level: str = "all", status: str = "open") -> dict:
    with SessionLocal() as s:
        q = s.query(_m.Alert).filter_by(studentId=student_id)
        if level != "all":
            q = q.filter(_m.Alert.level == level)
        if status != "all":
            q = q.filter(_m.Alert.status == status)
        rows = q.order_by(_m.Alert.createdAt.desc(), _m.Alert.id.desc()).all()
        items = [{
            "alertId": r.alertId or str(r.id), "level": r.level, "type": r.type,
            "title": r.title, "desc": r.desc, "trigger": r.trigger,
            "detail": json.loads(r.detail_json or "{}"),
            "createdAt": r.createdAt, "status": r.status,
            "suggestions": json.loads(r.suggestions_json or "[]"),
        } for r in rows]
    return {"total": len(items), "list": items}


def read_alert(alert_id: str) -> dict:
    with SessionLocal() as s:
        r = _alert_by_id(s, alert_id)
        if r:
            r.read = True
            r.status = "reviewed"
            s.commit()
            return {"alertId": alert_id, "read": True}
    return {"alertId": alert_id, "read": False}


def _alert_by_id(s, alert_id: str):
    r = s.query(_m.Alert).filter_by(alertId=alert_id).first()
    if r:
        return r
    return s.get(_m.Alert, int(alert_id)) if str(alert_id).isdigit() else None


def teacher_alerts(class_id: str = "", level: str = "all", status: str = "all",
                   type: str = "", kp_id: str = "", page: int = 1) -> dict:
    with SessionLocal() as s:
        ids = set(student_ids_of(s, class_id))
        q = s.query(_m.Alert)
        if ids:
            q = q.filter(_m.Alert.studentId.in_(ids))
        if level != "all":
            q = q.filter(_m.Alert.level == level)
        if status != "all":
            q = q.filter(_m.Alert.status == status)
        if type:
            q = q.filter(_m.Alert.type == type)
        rows = q.order_by(_m.Alert.id.desc()).all()
        items = []
        for r in rows:
            st = s.get(_m.Student, r.studentId)
            items.append({
                "alertId": r.alertId or str(r.id), "level": r.level,
                "student": (st.name if st else r.studentName) or r.studentId,
                "userId": r.studentId, "type": r.type or "掌握率过低",
                "kp": r.kp or _kp_name(s, r.kpId), "desc": r.desc or r.title,
                "trigger": r.trigger, "trendData": json.loads(r.trend_json or "[]") or [0, 0, 0, 0, 0],
                "createdAt": r.createdAt, "status": r.status,
            })
    return {"total": len(items), "list": items, "page": page}


def review_alert(alert_id: str, action: str, note: str = "") -> dict:
    with SessionLocal() as s:
        r = _alert_by_id(s, alert_id)
        if r:
            r.read = True
            r.status = "reviewed" if action != "ignore" else "ignored"
            if action == "ignore":
                r.level = "green"
            s.commit()
            return {"alertId": alert_id, "action": action, "ok": True}
    return {"alertId": alert_id, "ok": False}


def list_messages(student_id: str) -> dict:
    with SessionLocal() as s:
        rows = (s.query(_m.Message).filter_by(userId=student_id)
                .order_by(_m.Message.id.desc()).all())
        items = [{"msgId": r.msgId, "from": r.sender, "to": r.to, "title": r.title,
                  "content": r.content, "time": r.time, "read": r.read} for r in rows]
    return {"total": len(items), "list": items}


def send_message(student_id: str, sender: str, content: str, title: str = "教师私信") -> dict:
    with SessionLocal() as s:
        st = s.get(_m.Student, student_id)
        s.add(_m.Message(msgId="M" + uuid.uuid4().hex[:8], userId=student_id,
                         sender=sender, to=st.name if st else "", title=title,
                         content=content, time=_now(), read=False))
        s.commit()
    return {"ok": True}


# ---------------------------------------------------------------- 资源

def list_resources(type: str = "all", kp_id: str = "", keyword: str = "",
                   page: int = 1, size: int = 12) -> dict:
    with SessionLocal() as s:
        q = s.query(_m.Resource)
        if type and type != "all":
            q = q.filter(_m.Resource.type == type)
        if kp_id:
            q = q.filter(_m.Resource.kpId == kp_id)
        if keyword:
            q = q.filter(_m.Resource.title.contains(keyword))
        total = q.count()
        rows = q.offset((page - 1) * size).limit(size).all()
        items = [{"resId": r.resId, "type": r.type, "title": r.title, "kp": r.kp,
                  "duration": r.duration or "", "progress": r.progress, "views": r.views,
                  "source": r.source, "pages": r.pages} for r in rows]
    return {"total": total, "list": items, "page": page, "size": size}


# ---------------------------------------------------------------- 教师监测

def teacher_heatmap(class_id: str = "CL2301", dimension: str = "week") -> dict:
    """知识点 × 学生 掌握热力图（轴用名称展示，内部按 ID 关联）。"""
    with SessionLocal() as s:
        ids = set(student_ids_of(s, class_id))
        students = {x.userId: x for x in s.query(_m.Student).all()}
        kps = kp_index(s)
        recs = [r for r in s.query(_m.MasteryRecord).all() if (not ids or r.studentId in ids)]

        kp_ids = [k.kpId for k in sorted(kps.values(), key=lambda k: (k.orderNo, k.kpId))
                  if any(r.kpId == k.kpId for r in recs)]
        stu_ids = sorted({r.studentId for r in recs},
                         key=lambda u: (students[u].rank if u in students else 999, u))
        kp_idx = {k: i for i, k in enumerate(kp_ids)}
        stu_idx = {u: i for i, u in enumerate(stu_ids)}
        data = [[kp_idx[r.kpId], stu_idx[r.studentId], round(r.mastery)]
                for r in recs if r.kpId in kp_idx and r.studentId in stu_idx]

        kp_avg, sums = [], {}
        for r in recs:
            acc = sums.setdefault(r.kpId, [])
            acc.append(r.mastery)
        for k in kp_ids:
            kp_avg.append(round(sum(sums.get(k, [0])) / len(sums.get(k, [1]))))
        weakest = sorted(zip(kp_ids, kp_avg), key=lambda kv: kv[1])[:3]
        return {
            "dimension": dimension,
            "kpAxis": [kps[k].name for k in kp_ids],
            "studentAxis": [(students[u].name if u in students else u) for u in stu_ids],
            "data": data, "kpAvg": kp_avg,
            "weakest": [{"index": kp_idx[k], "name": kps[k].name, "avg": round1(v)}
                        for k, v in weakest],
        }


def teacher_students(class_id: str = "", alert_level: str = "all", keyword: str = "",
                     sort_by: str = "mastery", page: int = 1, size: int = 20) -> dict:
    with SessionLocal() as s:
        q = s.query(_m.Student)
        if class_id:
            q = q.filter(_m.Student.classId == class_id)
        if alert_level != "all":
            q = q.filter(_m.Student.alertLevel == alert_level)
        if keyword:
            q = q.filter(_m.Student.name.contains(keyword))
        rows_all = q.all()
        key = {"mastery": lambda x: x.masteryRate, "completion": lambda x: x.completionRate,
               "goal": lambda x: x.goalAchieveRate}.get(sort_by, lambda x: x.masteryRate)
        rows = sorted(rows_all, key=key, reverse=True)
        for r in rows:                       # 预警数用真实未处理预警覆盖档案值
            cnt = s.query(_m.Alert).filter_by(studentId=r.userId, status="open").count()
            r.alertCount = cnt
        items = [{"userId": r.userId, "name": r.name, "no": r.no, "avatar": r.avatar,
                  "completion": round1(r.completionRate), "mastery": round1(r.masteryRate),
                  "goal": round1(r.goalAchieveRate),
                  "alertLevel": r.alertLevel if r.alertCount else "green",
                  "alertCount": r.alertCount, "lastActive": r.lastActive or time_ago(_now()),
                  "studyMinutes": r.studyMinutes, "rank": r.rank} for r in rows]
        s.commit()
    return {"total": len(items), "list": items[(page - 1) * size: (page - 1) * size + size],
            "page": page, "size": size}


def student_profile(student_id: str) -> dict:
    """个体学情详情：画像指标 + 学习时间分布 + 活跃趋势 + 知识点明细 + 高频错题。"""
    with SessionLocal() as s:
        st = s.get(_m.Student, student_id)
        if not st:
            return {}
        peers = s.query(_m.Student).filter_by(classId=st.classId).all() or [st]
        subs = s.query(_m.Submission).filter_by(studentId=student_id).all()
        q2kp = {q.qId: q.kpId for q in s.query(_m.Question.qId, _m.Question.kpId).all()}
        questions = {q.qId: q for q in s.query(_m.Question).all()}
        kps = kp_index(s)
        mine = _mastery_of(s, student_id)

        # 知识点明细
        stat = {}
        for x in subs:
            kp = q2kp.get(x.qId, "")
            d = stat.setdefault(kp, {"questions": 0, "wrong": 0, "minutes": 0})
            d["questions"] += 1
            d["wrong"] += 0 if x.correct else 1
            d["minutes"] += int(x.duration or 0) // 60
        kp_detail = []
        for kp_id, d in sorted(stat.items(), key=lambda kv: -kv[1]["questions"])[:6]:
            m = round1(mine.get(kp_id, 0))
            kp_detail.append({"kpId": kp_id, "name": kps[kp_id].name if kp_id in kps else kp_id,
                              "mastery": round(m), "questions": d["questions"], "wrong": d["wrong"],
                              "minutes": d["minutes"], "level": level_of(m)})

        # 高频错题
        wrong_cnt = Counter(x.qId for x in subs if not x.correct)
        wrong_detail = []
        for qid, cnt in wrong_cnt.most_common(3):
            q = questions.get(qid)
            wrong_detail.append({
                "qId": qid, "kp": _kp_name(s, q.kpId) if q else "",
                "errorType": next((x.errorType for x in subs if x.qId == qid and not x.correct), "") or "概念混淆",
                "count": cnt, "difficulty": q.difficulty if q else 0,
            })

        # 学习时段分布
        dist = [0] * len(_TIME_BUCKETS)
        for x in subs:
            dt = parse_ts(x.ts)
            if not dt:
                continue
            for i, (_, lo, hi) in enumerate(_TIME_BUCKETS):
                if lo <= dt.hour < hi:
                    dist[i] += 1
                    break

        # 近 7 日活跃趋势
        days = s.query(_m.StudyDay).filter_by(studentId=student_id).all()
        by_day = {d.day: d for d in days}
        end = datetime.now(timezone.utc).date()
        x_axis, minutes, qs = [], [], []
        for i in range(6, -1, -1):
            day = (end - timedelta(days=i)).isoformat()
            d = by_day.get(day)
            x_axis.append(day[5:])
            minutes.append(int(d.minutes) if d else 0)
            qs.append(int(d.questions) if d else 0)

        return {
            "userId": st.userId, "name": st.name, "no": st.no, "className": st.className,
            "metrics": {
                "completion": round1(st.completionRate), "mastery": round1(st.masteryRate),
                "goal": round1(st.goalAchieveRate), "rank": st.rank,
                "totalStudents": len(peers),
                "accuracy": pct(sum(1 for x in subs if x.correct), len(subs)),
            },
            "studyTimeDist": {"xAxis": [b[0] for b in _TIME_BUCKETS], "data": dist},
            "activityTrend": {"xAxis": x_axis, "minutes": minutes, "questions": qs},
            "kpDetail": kp_detail, "wrongDetail": wrong_detail,
        }


# ---------------------------------------------------------------- 干预

def list_interventions(class_id: str = "", status: str = "all", scope: str = "all") -> dict:
    with SessionLocal() as s:
        q = s.query(_m.InterventionPlan)
        if status != "all":
            q = q.filter(_m.InterventionPlan.status == status)
        if scope != "all":
            q = q.filter(_m.InterventionPlan.scope == scope)
        rows = q.order_by(_m.InterventionPlan.id.desc()).all()
        items = [{
            "ivId": r.planId, "status": r.status, "level": r.level or "warn",
            "alertId": r.alertId, "scope": r.scope or r.type, "title": r.title,
            "target": r.target, "reason": r.reason,
            "steps": json.loads(r.content or "[]"), "expectEffect": r.expectEffect,
            "resources": json.loads(r.resources_json or "[]"), "packId": r.packId,
            "createdAt": r.createdAt,
        } for r in rows]
    return {"total": len(items), "list": items}


def confirm_intervention(iv_id: str, steps: list = None, resources: list = None, note: str = "") -> dict:
    with SessionLocal() as s:
        r = s.query(_m.InterventionPlan).filter_by(planId=iv_id).first()
        if r:
            r.status = "running"
            if steps is not None:
                r.content = json.dumps(steps, ensure_ascii=False)
            if resources is not None:
                r.resources_json = json.dumps(resources, ensure_ascii=False)
            s.commit()
            return {"ivId": iv_id, "ok": True, "status": "running"}
    return {"ivId": iv_id, "ok": False}


def reject_intervention(iv_id: str) -> dict:
    with SessionLocal() as s:
        r = s.query(_m.InterventionPlan).filter_by(planId=iv_id).first()
        if r:
            r.status = "rejected"
            s.commit()
            return {"ivId": iv_id, "ok": True, "status": "rejected"}
    return {"ivId": iv_id, "ok": False}
