"""配置型数据服务：练习模式 / 出题配置 / 教学方法 / 素材库。

「配置项」（练习模式定义、题型字典、教学方法）属于业务常量，写在代码里；
「数据项」（素材库文件、知识点选项、各模式可选题量）一律查真实表。
"""
import uuid

from ..db import models as _m
from ..db.session import SessionLocal
from .common import now_str

# 练习模式（业务配置，count 由真实题量在查询时填充）
PRACTICE_MODES = [
    {"key": "weak", "name": "薄弱点强化", "desc": "系统按掌握率自动组卷，命中薄弱知识点",
     "icon": "target", "recommend": True},
    {"key": "order", "name": "顺序练习", "desc": "按章节与知识点前后置顺序逐题推进",
     "icon": "list", "recommend": False},
    {"key": "random", "name": "随机练习", "desc": "在已学范围内随机抽题，检验综合掌握",
     "icon": "shuffle", "recommend": False},
    {"key": "wrong", "name": "错题重练", "desc": "重做历史错题，验证是否真正掌握",
     "icon": "refresh", "recommend": False},
]

TYPE_OPTIONS = [
    {"key": "single", "name": "单选题"}, {"key": "multi", "name": "多选题"},
    {"key": "judge", "name": "判断题"}, {"key": "blank", "name": "填空题"},
    {"key": "code", "name": "算法设计题"},
]

# 教学方法（AI 答疑的方法选择；AI 暂缓时仍需在前端展示方法目录）
TEACHING_METHODS = [
    {"key": "lecture", "name": "讲授法", "desc": "系统讲解概念与原理，结构清晰", "icon": "book"},
    {"key": "guided", "name": "引导式", "desc": "不直接给答案，层层提问引导思考", "icon": "compass"},
    {"key": "case", "name": "案例式", "desc": "结合实际工程案例说明", "icon": "briefcase"},
    {"key": "heuristic", "name": "启发式", "desc": "从反例与矛盾中启发理解", "icon": "bulb"},
    {"key": "fun", "name": "趣味式", "desc": "类比与故事化表达，降低认知门槛", "icon": "smile"},
]


def practice_modes(student_id: str = "") -> list:
    """练习模式 + 各模式当前可选题量（真实统计）。"""
    with SessionLocal() as s:
        total = s.query(_m.Question).filter(_m.Question.answer != "").count()
        weak_kps = []
        if student_id:
            weak_kps = [r.kpId for r in s.query(_m.MasteryRecord)
                        .filter(_m.MasteryRecord.studentId == student_id,
                                _m.MasteryRecord.mastery < 70).all()]
        weak_n = (s.query(_m.Question)
                  .filter(_m.Question.answer != "", _m.Question.kpId.in_(weak_kps)).count()
                  if weak_kps else min(10, total))
        wrong_n = 0
        if student_id:
            wrong_n = sum(1 for x in s.query(_m.Submission)
                          .filter_by(studentId=student_id, correct=False, mastered=False).all())
        counts = {"weak": max(1, min(20, weak_n)), "order": min(20, total),
                  "random": min(15, total), "wrong": min(12, max(1, wrong_n))}
        return [{**m, "count": counts.get(m["key"], 10)} for m in PRACTICE_MODES]


def gen_config(class_id: str = "") -> dict:
    with SessionLocal() as s:
        materials = [{
            "fileId": m.fileId, "name": m.name, "size": m.size, "type": m.type,
            "status": m.status, "kpCount": m.kpCount, "progress": m.progress,
        } for m in s.query(_m.Material).order_by(_m.Material.fileId).all()]
        kp_options = [{"kpId": k.kpId, "name": k.name} for k in
                      s.query(_m.KnowledgePoint).order_by(_m.KnowledgePoint.orderNo).all()]
    return {"materials": materials, "kpOptions": kp_options, "typeOptions": TYPE_OPTIONS}


def add_material(name: str, size: str = "", mtype: str = "doc") -> dict:
    """上传素材：真实落库，状态 parsing（解析完成后由任务置为 parsed）。"""
    fid = "F" + uuid.uuid4().hex[:8]
    with SessionLocal() as s:
        s.add(_m.Material(fileId=fid, name=name, size=size or "—", type=mtype,
                          status="parsing", kpCount=0, progress=0, uploadedAt=now_str()))
        s.commit()
    return {"fileId": fid, "status": "parsing", "progress": 0}


def teaching_methods() -> list:
    return TEACHING_METHODS
