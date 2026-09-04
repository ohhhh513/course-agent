"""学情分析报告服务：真实生成 + 落库归档 + 历史回看。

报告内容全部由真实表统计生成（班级概览、共性短板、个体预警、干预效果、
目标达成、教学建议），生成后写入 `reports` 表，历史列表与详情都从库里读，
不再是写死的快照。
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from ..db import models as _m
from ..db.session import SessionLocal
from .analysis import error_analysis
from .common import class_kp_mastery, jload, kp_index, now_str, pct, round1, student_ids_of
from .graph import goal_graph

_GENERATOR = "课程智能体学情分析引擎 v1.0"


def list_reports(class_id: str = "") -> list:
    with SessionLocal() as s:
        q = s.query(_m.Report)
        if class_id:
            q = q.filter(_m.Report.classId == class_id)
        rows = q.order_by(_m.Report.createdAt.desc()).all()
        return [{
            "reportId": r.reportId, "title": r.title, "scope": r.scope,
            "period": r.period, "createdAt": r.createdAt, "creator": r.creator,
            "status": r.status, "pages": r.pages,
        } for r in rows]


def get_report(report_id: str) -> dict:
    with SessionLocal() as s:
        r = s.get(_m.Report, report_id) or (
            s.query(_m.Report).order_by(_m.Report.createdAt.desc()).first())
        if not r:
            return {}
        return {"reportId": r.reportId, "title": r.title,
                "meta": jload(r.meta_json, {}), "sections": jload(r.sections_json, [])}


def generate_report(payload: dict, creator: str = "教师") -> dict:
    """按班级/章节/时间区间生成报告并落库。"""
    p = payload or {}
    class_id = p.get("classId") or "CL2301"
    chapter = p.get("chapter") or "全课程"
    start = p.get("startDate") or (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%d")
    end = p.get("endDate") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    period = f"{start} ~ {end}"

    with SessionLocal() as s:
        ids = student_ids_of(s, class_id)
        students = s.query(_m.Student).filter(_m.Student.classId == class_id).all() if class_id else []
        if not students:
            students = s.query(_m.Student).all()
            ids = [x.userId for x in students]
        cls = s.get(_m.ClassGroup, class_id) if class_id else None
        n = len(ids) or 1
        kp_avg = class_kp_mastery(s, ids)
        kps = kp_index(s)
        avg_mastery = round1(sum(kp_avg.values()) / len(kp_avg)) if kp_avg else 0.0
        avg_completion = round1(sum(x.completionRate for x in students) / len(students)) if students else 0.0
        avg_goal = round1(sum(x.goalAchieveRate for x in students) / len(students)) if students else 0.0

        ea = error_analysis(class_id=class_id, chapter="" if chapter == "全课程" else chapter)
        weakest = sorted(kp_avg.items(), key=lambda kv: kv[1])[:3]
        goals = goal_graph(class_id=class_id).get("nodes", [])
        unit_goals = [g for g in goals if g["category"] == 1]

        open_alerts = [a for a in s.query(_m.Alert).filter_by(status="open").all() if a.studentId in set(ids)]
        red_alerts = [a for a in open_alerts if a.level == "red"]
        running_iv = s.query(_m.InterventionPlan).filter_by(status="running").count()
        done_iv = s.query(_m.InterventionPlan).filter_by(status="done").count()

        sections = [
            {
                "title": "一、整体掌握度",
                "paragraphs": [
                    f"截至 {end}，{cls.name if cls else class_id} 共 {len(students)} 名学生纳入统计，"
                    f"知识点平均掌握率 {avg_mastery}%，平均完成率 {avg_completion}%，"
                    f"能力目标平均达成度 {avg_goal}%。"
                ],
                "bullets": [
                    f"平均掌握率 {avg_mastery}%（{'达标' if avg_mastery >= 75 else '低于达标线 75%'}）",
                    f"平均完成率 {avg_completion}%，目标达成度 {avg_goal}%",
                    f"统计覆盖 {len(kp_avg)} 个知识点，累计作答 "
                    f"{s.query(func.count(_m.Submission.id)).filter(_m.Submission.studentId.in_(ids)).scalar() if ids else 0} 题",
                ],
            },
            {
                "title": "二、共性短板与归因",
                "paragraphs": [
                    f"班级共性薄弱知识点集中在 "
                    f"{'、'.join(kps[k].name if k in kps else k for k, _ in weakest) or '—'}，"
                    f"建议安排课堂集体干预。"
                ],
                "bullets": [
                    f"{kps[k].name if k in kps else k}：班级掌握率 {v}%，"
                    f"{sum(1 for c in ea['commonVsIndividual']['common'] if c['kp'] == (kps[k].name if k in kps else k)) and '需重点干预' or '建议课堂回顾'}"
                    for k, v in weakest
                ] or ["暂无明显的共性短板"],
            },
            {
                "title": "三、个体预警情况",
                "paragraphs": [
                    f"当前共有 {len(open_alerts)} 条未处理预警，其中红色预警 {len(red_alerts)} 条。"
                ],
                "bullets": [
                    f"{s.get(_m.Student, a.studentId).name if s.get(_m.Student, a.studentId) else a.studentId}"
                    f" · {a.title}（{a.level}）" for a in open_alerts[:5]
                ] or ["暂无未处理预警，班级整体平稳"],
            },
            {
                "title": "四、干预效果验证",
                "paragraphs": [
                    f"已确认执行 {running_iv} 项干预、已完成 {done_iv} 项。"
                    f"建议对已完成干预的知识点做一次复测，对比干预前后掌握率变化。"
                ],
                "bullets": [
                    f"待确认干预建议 {s.query(_m.InterventionPlan).filter_by(status='pending').count()} 项",
                    f"执行中 {running_iv} 项 / 已完成 {done_iv} 项",
                    "复测方式：对干预知识点组 10 题靶向练习，对比班级平均掌握率",
                ],
            },
            {
                "title": "五、能力目标达成度",
                "paragraphs": [
                    f"课程总目标达成度 {round1(sum(g['achieve'] for g in unit_goals) / len(unit_goals)) if unit_goals else 0}%，"
                    f"各单元目标达成情况见下表。"
                ],
                "bullets": [
                    f"{g['name']}：{g['achieve']}%（权重 {g['weight']}%）" for g in unit_goals
                ] or ["暂无目标数据"],
            },
            {
                "title": "六、下阶段教学建议",
                "paragraphs": [
                    "基于上述共性短板与个体预警，建议按「课堂集体补讲 → 靶向练习 → 复测验证」的节奏推进。"
                ],
                "bullets": [
                    f"课堂补讲：{'、'.join(kps[k].name if k in kps else k for k, _ in weakest[:2]) or '—'}",
                    f"靶向练习：为 {len({a.studentId for a in red_alerts})} 名红色预警学生推送个性化练习包",
                    f"复盘归因：{ea['causes'][0]['title'] if ea.get('causes') else '—'}",
                ],
            },
        ]

        pages = max(1, round(len(sections) / 2))
        rid = "RP" + datetime.now(timezone.utc).strftime("%Y%m%d") + uuid.uuid4().hex[:4].upper()
        meta = {
            "className": cls.name if cls else (students[0].className if students else class_id),
            "studentCount": len(students), "chapter": chapter, "period": period,
            "generatedAt": now_str(), "generator": _GENERATOR,
        }
        s.add(_m.Report(
            reportId=rid, title=f"{meta['className']} {chapter} 学情分析报告",
            scope=chapter, period=period, createdAt=now_str(), creator=creator,
            status="ready", pages=pages, classId=class_id,
            meta_json=_dump(meta), sections_json=_dump(sections),
        ))
        s.commit()
        return {"reportId": rid, "title": f"{meta['className']} {chapter} 学情分析报告",
                "meta": meta, "sections": sections}


def _dump(obj) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False)
