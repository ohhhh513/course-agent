"""三大课程图谱 + 学习路径。

设计要点
--------
图谱的**结构与静态属性**（层级、章节、难度、学时、权重）来自 `graph_nodes` 表；
**动态属性**（掌握率、错误率、达成度）在查询时用真实表计算并覆盖静态值，
因此图谱永远反映当前学情，而不是一份写死的快照。

- 知识图谱：掌握率 = mastery_records（个人 or 班级均值）
- 问题图谱：错误率 = submissions 中该问题关联知识点的答错占比
- 目标图谱：达成度 = 目标关联知识点的平均掌握率（权重来自节点配置）
- 学习路径：知识点按 orderNo（学习顺序）展开，状态由掌握率推导
"""
from ..db import models as _m
from ..db.session import SessionLocal
from .common import class_kp_mastery, jload, kp_index, mastery_of, round1, student_ids_of

# 图例为前端展示配置（与 mock_data.json 保持一致）
CATEGORIES = {
    "knowledge": [
        {"name": "已掌握", "color": "#22c55e"},
        {"name": "学习中", "color": "#6366f1"},
        {"name": "待加强", "color": "#f59e0b"},
        {"name": "未开始", "color": "#64748b"},
        {"name": "薄弱预警", "color": "#ef4444"},
    ],
    "problem": [
        {"name": "驱动问题", "color": "#8b5cf6"},
        {"name": "子问题", "color": "#38bdf8"},
        {"name": "关联知识点", "color": "#6366f1"},
        {"name": "高频错题簇", "color": "#ef4444"},
    ],
    "goal": [
        {"name": "课程总目标", "color": "#8b5cf6"},
        {"name": "单元目标", "color": "#06b6d4"},
        {"name": "知识点目标", "color": "#6366f1"},
    ],
}

_GRAPH_KEYS = {"knowledge", "problem", "goal"}


def _category_of(mastery: float) -> int:
    """掌握率 → 知识图谱分类（对应 CATEGORIES.knowledge 下标）。"""
    if mastery >= 85:
        return 0        # 已掌握
    if mastery >= 70:
        return 1        # 学习中
    if mastery >= 60:
        return 2        # 待加强
    if mastery > 0:
        return 4        # 薄弱预警
    return 3            # 未开始


def _real_mastery(s, student_id: str = "", class_id: str = "") -> dict:
    if student_id:
        return mastery_of(s, student_id)
    return class_kp_mastery(s, student_ids_of(s, class_id))


def knowledge_graph(student_id: str = "", class_id: str = "", course_id: str = "") -> dict:
    with SessionLocal() as s:
        mastery = _real_mastery(s, student_id, class_id)
        nodes = []
        for n in (s.query(_m.GraphNode).filter_by(graphType="knowledge")
                  .order_by(_m.GraphNode.orderNo).all()):
            payload = jload(n.payload_json, {})
            m = round1(mastery.get(n.nodeId, payload.get("mastery", 0)))
            nodes.append({
                "id": n.nodeId, "name": n.name,
                "chapter": payload.get("chapter", 0),
                "category": _category_of(m),
                "mastery": round(m),
                "difficulty": payload.get("difficulty", 1),
                "isKey": bool(payload.get("isKey", False)),
                "hours": payload.get("hours", 0),
            })
        links = [{"source": l.sourceId, "target": l.targetId, "relation": l.relation}
                 for l in s.query(_m.GraphLink).filter_by(graphType="knowledge").all()]
    return {"graphType": "knowledge", "categories": CATEGORIES["knowledge"],
            "nodes": nodes, "links": links}


def problem_graph(class_id: str = "", student_id: str = "") -> dict:
    with SessionLocal() as s:
        ids = student_ids_of(s, class_id)
        q2kp = {q.qId: q.kpId for q in s.query(_m.Question.qId, _m.Question.kpId).all()}
        wrong, total = {}, {}
        for sub in s.query(_m.Submission).all():
            if ids and sub.studentId not in set(ids):
                continue
            kp = q2kp.get(sub.qId, "")
            if not kp:
                continue
            total[kp] = total.get(kp, 0) + 1
            if not sub.correct:
                wrong[kp] = wrong.get(kp, 0) + 1

        nodes = []
        for n in (s.query(_m.GraphNode).filter_by(graphType="problem")
                  .order_by(_m.GraphNode.orderNo).all()):
            payload = jload(n.payload_json, {})
            node = {"id": n.nodeId, "name": n.name, "category": n.category,
                    "level": payload.get("level", 1)}
            if "relatedKp" in payload:
                node["relatedKp"] = payload["relatedKp"]
            if "count" in payload:
                node["count"] = payload["count"]
            # 错误率：节点关联知识点的真实答错占比（无数据时沿用配置基线）
            kp_ids = payload.get("kpIds") or []
            if kp_ids:
                t = sum(total.get(k, 0) for k in kp_ids)
                w = sum(wrong.get(k, 0) for k in kp_ids)
                if t:
                    node["errorRate"] = round(w / t * 100)
                elif "errorRate" in payload:
                    node["errorRate"] = payload["errorRate"]
            elif "errorRate" in payload:
                node["errorRate"] = payload["errorRate"]
            nodes.append(node)
        links = [{"source": l.sourceId, "target": l.targetId, "relation": l.relation}
                 for l in s.query(_m.GraphLink).filter_by(graphType="problem").all()]
    return {"graphType": "problem", "categories": CATEGORIES["problem"],
            "nodes": nodes, "links": links}


def goal_graph(student_id: str = "", class_id: str = "") -> dict:
    with SessionLocal() as s:
        mastery = _real_mastery(s, student_id, class_id)
        all_vals = list(mastery.values())
        overall = round1(sum(all_vals) / len(all_vals)) if all_vals else 0.0
        nodes = []
        for n in (s.query(_m.GraphNode).filter_by(graphType="goal")
                  .order_by(_m.GraphNode.orderNo).all()):
            payload = jload(n.payload_json, {})
            kp_ids = payload.get("kpIds") or []
            if kp_ids:
                vals = [mastery.get(k) for k in kp_ids if mastery.get(k) is not None]
                achieve = round1(sum(vals) / len(vals)) if vals else 0.0
            else:
                achieve = overall                       # 课程总目标 = 全知识点均值
            nodes.append({"id": n.nodeId, "name": n.name, "category": n.category,
                          "achieve": achieve, "weight": payload.get("weight", 0)})
        links = [{"source": l.sourceId, "target": l.targetId, "relation": l.relation}
                 for l in s.query(_m.GraphLink).filter_by(graphType="goal").all()]
    return {"graphType": "goal", "categories": CATEGORIES["goal"],
            "nodes": nodes, "links": links}


def learning_path(student_id: str = "", course_id: str = "") -> list:
    with SessionLocal() as s:
        mastery = mastery_of(s, student_id) if student_id else {}
        res_count = {}
        for r in s.query(_m.Resource.kpId).all():
            if r[0]:
                res_count[r[0]] = res_count.get(r[0], 0) + 1
        out, step = [], 0
        for kp in (s.query(_m.KnowledgePoint).order_by(_m.KnowledgePoint.orderNo,
                                                       _m.KnowledgePoint.kpId).all()):
            step += 1
            m = round1(mastery.get(kp.kpId, 0))
            if m >= 85:
                status = "done"
            elif m <= 0:
                status = "todo"
            elif m < 60:
                status = "warn"
            else:
                status = "doing"
            out.append({
                "step": step, "kpId": kp.kpId, "name": kp.name,
                "chapter": kp.chapterName or (f"第{kp.chapter}章" if kp.chapter else ""),
                "status": status, "hours": kp.hours or 2,
                "mastery": round(m), "resCount": res_count.get(kp.kpId, 0),
            })
    return out


def kp_detail(kp_id: str, student_id: str = "", class_id: str = "") -> dict:
    """知识点详情：结构（前后置）+ 真实掌握情况 + 资源 + 题目统计。"""
    with SessionLocal() as s:
        kp = s.get(_m.KnowledgePoint, kp_id)
        if not kp:
            return {}
        kps = kp_index(s)
        my = mastery_of(s, student_id) if student_id else {}
        cls_avg = class_kp_mastery(s, student_ids_of(s, class_id)) if class_id else {}

        def _objs(ids):
            return [{"kpId": i, "name": kps[i].name if i in kps else i,
                     "mastery": round(my.get(i, cls_avg.get(i, 0)))} for i in ids]

        pre = _objs(jload(kp.preKp, []))
        post = _objs(jload(kp.postKp, []))

        resources = [{
            "resId": r.resId, "type": r.type, "title": r.title,
            "duration": r.duration or "", "pages": r.pages or 0,
            "source": r.source, "progress": r.progress,
        } for r in s.query(_m.Resource).filter_by(kpId=kp_id).all()]

        qcount = s.query(_m.Question).filter_by(kpId=kp_id).count()
        wrong = (s.query(_m.Submission)
                 .join(_m.Question, _m.Submission.qId == _m.Question.qId)
                 .filter(_m.Question.kpId == kp_id, _m.Submission.correct.is_(False),
                         _m.Submission.studentId == student_id).count()) if student_id else 0

        related = jload(kp.desc, []) if kp.desc else []
        return {
            "kpId": kp.kpId, "name": kp.name,
            "chapter": kp.chapterName or (f"第{kp.chapter}章" if kp.chapter else ""),
            "difficulty": kp.difficulty, "isKey": kp.isKey, "hours": kp.hours,
            "summary": kp.summary or "",
            "completionRate": round(next((r.completion for r in s.query(_m.MasteryRecord)
                                          .filter_by(studentId=student_id, kpId=kp_id).all()), 0)),
            "masteryRate": round(my.get(kp_id, 0)),
            "classAvgMastery": round(cls_avg.get(kp_id, 0)),
            "pre": pre, "post": post, "resources": resources,
            "questionCount": qcount, "wrongCount": wrong,
            "relatedProblems": related,
        }
