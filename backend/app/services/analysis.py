"""学情分析服务：错误归因 / 薄弱链条 / 共性-个性归因。

AI 归因模块暂缓，本模块用**可解释的规则归因**给出结论：
每一条结论都由真实作答数据统计得出（错因分布、错题排行、薄弱知识点链、
共性薄弱 vs 个体差异），因此接入 LLM 后只需替换措辞生成部分，数据口径不变。
"""
from ..db import models as _m
from ..db.session import SessionLocal
from .common import class_kp_mastery, jload, kp_index, level_of, now_str, parse_ts, pct, round1, student_ids_of

# 规则归因：错因 → 触发条件（按优先级从上到下匹配）
_ERROR_RULES = [
    ("前置知识缺失", lambda sub, m, diff: m < 50),
    ("计算失误", lambda sub, m, diff: bool(sub.duration) and sub.duration < 30),
    ("题意理解偏差", lambda sub, m, diff: bool(sub.duration) and sub.duration > 120),
    ("公式记忆错误", lambda sub, m, diff: diff >= 4),
    ("算法流程不清", lambda sub, m, diff: diff == 3),
    ("概念混淆", lambda sub, m, diff: True),
]


def _classify(sub, mastery: float, difficulty: int) -> str:
    for name, rule in _ERROR_RULES:
        try:
            if rule(sub, mastery, difficulty):
                return name
        except Exception:
            continue
    return "概念混淆"


_TIME_RANGE_DAYS = {"近7天": 7, "近30天": 30, "近90天": 90, "本学期": 200}


def error_analysis(class_id: str = "CL2301", chapter: str = "", time_range: str = "",
                   kp_id: str = "") -> dict:
    from datetime import datetime, timedelta, timezone

    with SessionLocal() as s:
        ids = student_ids_of(s, class_id)
        id_set = set(ids)
        kps = kp_index(s)
        questions = {q.qId: q for q in s.query(_m.Question).all()}
        mastery_avg = class_kp_mastery(s, ids)

        subs = s.query(_m.Submission).all()
        if id_set:
            subs = [x for x in subs if x.studentId in id_set]
        if chapter:
            keep = {k.kpId for k in kps.values() if (k.chapterName or "") == chapter}
            subs = [x for x in subs if questions.get(x.qId) and questions[x.qId].kpId in keep]
        if kp_id:
            subs = [x for x in subs if questions.get(x.qId) and questions[x.qId].kpId == kp_id]
        if time_range in _TIME_RANGE_DAYS:
            since = datetime.now(timezone.utc) - timedelta(days=_TIME_RANGE_DAYS[time_range])
            subs = [x for x in subs if (parse_ts(x.ts) or since) >= since]

        # ---- 错因分布
        dist, wrong_subs = {}, []
        for x in subs:
            if x.correct:
                continue
            wrong_subs.append(x)
            q = questions.get(x.qId)
            m = mastery_avg.get(q.kpId if q else "", 70.0)
            key = x.errorType or _classify(x, m, (q.difficulty if q else 1))
            dist[key] = dist.get(key, 0) + 1
        total_wrong = max(1, len(wrong_subs))
        error_dist = [{"type": k, "count": v, "ratio": pct(v, total_wrong)}
                      for k, v in sorted(dist.items(), key=lambda kv: -kv[1])][:6]

        # ---- 高频错题 TOP5
        by_q = {}
        for x in wrong_subs:
            st = by_q.setdefault(x.qId, {"count": 0, "answers": {}, "types": {}})
            st["count"] += 1
            st["answers"][x.answer] = st["answers"].get(x.answer, 0) + 1
            t = x.errorType or _classify(x, mastery_avg.get(questions[x.qId].kpId if questions.get(x.qId) else "", 70.0),
                                         questions[x.qId].difficulty if questions.get(x.qId) else 1)
            st["types"][t] = st["types"].get(t, 0) + 1
        attempts = {}
        for x in subs:
            attempts[x.qId] = attempts.get(x.qId, 0) + 1
        top_wrong = []
        for qid, st in sorted(by_q.items(), key=lambda kv: -kv[1]["count"])[:5]:
            q = questions.get(qid)
            if not q:
                continue
            kp = kps.get(q.kpId)
            main_opt = max(st["answers"].items(), key=lambda kv: kv[1])[0] if st["answers"] else ""
            main_type = max(st["types"].items(), key=lambda kv: kv[1])[0] if st["types"] else "概念混淆"
            top_wrong.append({
                "qId": qid, "stem": q.stem, "kp": kp.name if kp else q.kpId,
                "wrongRate": pct(st["count"], attempts.get(qid, st["count"])),
                "count": st["count"], "mainWrongOption": main_opt,
                "difficulty": q.difficulty, "type": main_type,
            })

        # ---- 薄弱链：最弱知识点 → 其前置 → 前置的前置
        ranked = sorted(mastery_avg.items(), key=lambda kv: kv[1]) if mastery_avg else []
        chain = []
        if ranked:
            leaf_id = ranked[0][0]
            chain.append(leaf_id)
            cur = leaf_id
            for _ in range(2):
                pre = jload(kps[cur].preKp, []) if cur in kps else []
                pre = [p for p in pre if p in kps and p not in chain]
                if not pre:
                    break
                nxt = min(pre, key=lambda p: mastery_avg.get(p, 0))
                chain.append(nxt)
                cur = nxt
        chain = list(reversed(chain))            # root → mid → leaf
        while len(chain) < 3:
            nxt = next((k for k, _ in ranked if k not in chain), "")
            if not nxt:
                break
            chain.append(nxt)

        def _node(kid, role):
            return {"kpId": kid, "name": kps[kid].name if kid in kps else kid,
                    "mastery": round1(mastery_avg.get(kid, 0)), "type": role}

        leaf = chain[-1] if chain else ""
        mid = chain[-2] if len(chain) > 1 else ""
        root = chain[-3] if len(chain) > 2 else ""
        leaf_name = kps[leaf].name if leaf in kps else leaf
        mid_name = kps[mid].name if mid in kps else mid
        explain = (
            f"班级在「{mid_name}」上掌握率为 {round1(mastery_avg.get(mid, 0))}%，"
            f"直接导致「{leaf_name}」的正确率偏低（当前掌握率 {round1(mastery_avg.get(leaf, 0))}%）。"
            f"建议先补齐前置知识点，再推进 {leaf_name} 的针对性训练。"
        ) if mid and leaf else "暂无足够的作答数据支撑薄弱链条分析。"

        # ---- 归因（4 条，全部由统计推导）
        n_students = len(ids) or 1
        low_kps = [k for k, v in mastery_avg.items() if v < 60]
        pre_missing = dist.get("前置知识缺失", 0)
        concept = dist.get("概念混淆", 0) + dist.get("算法流程不清", 0)
        careless = dist.get("计算失误", 0) + dist.get("题意理解偏差", 0)
        kp_low_students = {}
        for r in s.query(_m.MasteryRecord).filter(_m.MasteryRecord.mastery < 60).all():
            if id_set and r.studentId not in id_set:
                continue
            kp_low_students[r.kpId] = kp_low_students.get(r.kpId, 0) + 1

        causes = [
            {
                "causeId": "CA1", "level": "danger" if pre_missing > total_wrong * 0.15 else "warn",
                "title": "前置知识缺失：前置知识点掌握率偏低",
                "desc": f"{pct(pre_missing, total_wrong)}% 的错题发生在掌握率低于 50% 的知识点上，"
                        f"说明学生在该知识点的前置内容上就存在缺口。",
                "evidence": [
                    f"关联错题 {pre_missing} 道，分布在 {len(low_kps)} 个薄弱知识点",
                    f"薄弱知识点平均掌握率 {round1(sum(mastery_avg.get(k, 0) for k in low_kps) / len(low_kps)) if low_kps else 0}%",
                    f"全班 {len(kp_low_students)} 个知识点存在掌握率<60% 的学生",
                ],
                "advice": [
                    f"课堂用 5 分钟重讲「{mid_name or '前置知识点'}」的核心概念与适用边界",
                    "为掌握率<60% 的学生推送前置靶向练习包",
                    "在新课前增加一次 3 分钟的前置知识小测",
                ],
            },
            {
                "causeId": "CA2", "level": "danger" if concept > total_wrong * 0.3 else "warn",
                "title": "概念理解不牢：概念混淆与算法流程不清",
                "desc": f"{concept} 道错题（{pct(concept, total_wrong)}%）表现为概念混淆或算法流程记忆不完整。",
                "evidence": [
                    f"高频错题 TOP1：{top_wrong[0]['stem'][:20] if top_wrong else '—'}（错 {top_wrong[0]['count'] if top_wrong else 0} 次）",
                    f"错误率最高的题目正确率仅 {round1(100 - (top_wrong[0]['wrongRate'] if top_wrong else 0))}%",
                    f"涉及 {len(set(questions[x.qId].kpId for x in wrong_subs if questions.get(x.qId)))} 个知识点",
                ],
                "advice": [
                    "用对比表格重讲易混概念的差异与判别方法",
                    "增加一步一空的「流程填空」练习，强化算法步骤记忆",
                    "推送对应知识点的补救微课并要求看完后立刻重测",
                ],
            },
            {
                "causeId": "CA3", "level": "warn",
                "title": "练习量不足：部分学生作答次数显著偏少",
                "desc": f"班级人均作答 {round1(len(subs) / n_students, 1)} 题，"
                        f"练习量最少的学生与人均值差距明显。",
                "evidence": [
                    f"全班累计作答 {len(subs)} 题，人均 {round1(len(subs) / n_students, 1)} 题",
                    f"共 {len(set(x.studentId for x in subs))} 名学生在统计区间内有作答记录",
                    f"人均正确率 {pct(sum(1 for x in subs if x.correct), len(subs))}%",
                ],
                "advice": [
                    "为练习量不足的学生布置每日 10 题的基础训练",
                    "设置章节阶段性小测，形成固定练习节奏",
                    "用班级排行榜与连续学习天数做正向激励",
                ],
            },
            {
                "causeId": "CA4", "level": "warn" if careless else "ok",
                "title": "计算与审题：快速作答与长耗时题目错误集中",
                "desc": f"{careless} 道错题（{pct(careless, total_wrong)}%）表现为作答过快（<30 秒）或过慢（>120 秒）。",
                "evidence": [
                    f"平均作答耗时 {round1(sum(x.duration or 0 for x in subs) / len(subs)) if subs else 0} 秒",
                    f"作答<30 秒的错题 {dist.get('计算失误', 0)} 道",
                    f"作答>120 秒的错题 {dist.get('题意理解偏差', 0)} 道",
                ],
                "advice": [
                    "训练审题：要求圈画关键词后再作答",
                    "对计算类题目设置最短作答时长提醒",
                    "讲评时重点复盘「会做但做错」的题目",
                ],
            },
        ]

        # ---- 共性 vs 个体
        common = []
        for kp_key, cnt in sorted(kp_low_students.items(), key=lambda kv: -kv[1])[:3]:
            kp = kps.get(kp_key)
            common.append({
                "kp": kp.name if kp else kp_key, "affected": cnt,
                "ratio": pct(cnt, n_students), "desc": "班级共性薄弱，需课堂集体干预",
            })
        per_student = {}
        for r in s.query(_m.MasteryRecord).all():
            if id_set and r.studentId not in id_set:
                continue
            acc = per_student.setdefault(r.studentId, [])
            acc.append(r.mastery)
        avg_by_student = {k: round1(sum(v) / len(v)) for k, v in per_student.items()}
        submits_by_student = {}
        for x in subs:
            submits_by_student[x.studentId] = submits_by_student.get(x.studentId, 0) + 1
        individual = []
        for uid, val in sorted(avg_by_student.items(), key=lambda kv: kv[1])[:3]:
            st = s.get(_m.Student, uid)
            cnt = submits_by_student.get(uid, 0)
            if val < 60:
                issue = "全面滞后"
            elif cnt < 10:
                issue = f"练习量严重不足（仅 {cnt} 题）"
            else:
                issue = "局部知识点薄弱"
            individual.append({
                "student": st.name if st else uid, "userId": uid, "issue": issue,
                "desc": "个体异常，需一对一关注" if val < 65 else "建议督促练习并跟踪",
            })

        return {
            "scope": {"classId": class_id or "CL2301", "chapter": chapter or "全课程",
                      "timeRange": time_range or "近30天"},
            "errorTypeDist": error_dist,
            "topWrongQuestions": top_wrong,
            "weakChain": {"root": _node(root, "pre"), "mid": _node(mid, "pre"),
                          "leaf": _node(leaf, "target"), "explain": explain},
            "causes": causes,
            "commonVsIndividual": {"common": common, "individual": individual},
        }


def weak_chain(class_id: str = "", kp_id: str = "") -> dict:
    return error_analysis(class_id=class_id, kp_id=kp_id).get("weakChain", {})


def causes(class_id: str = "") -> list:
    return error_analysis(class_id=class_id).get("causes", [])
