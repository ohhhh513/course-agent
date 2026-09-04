"""知识图谱 / 问题图谱 / 目标图谱 / 学习路径 / 知识点详情。

关键设计：**静态属性存图、动态属性实算**。
GraphNode.payload_json 保存拓扑与静态属性（名称、层级、坐标），
而 mastery / errorRate / achieve 这类会随学习行为变化的属性，
在**每次查询时**用真实表（mastery_records / submissions）覆盖写入，
这样图谱永远反映当前学情，不需要任何后台刷新任务。
"""
from fastapi import APIRouter, Depends, Query

from ..core.envelope import Envelope, ok
from ..core.security import UserClaims, get_current_user
from .. import repo
from ..services import graph as svc_graph
from ._ctx import class_id_of, DEFAULT_COURSE

router = APIRouter(prefix="/graph", tags=["graph"])

_BUILDERS = {
    "knowledge": svc_graph.knowledge_graph,
    "problem": svc_graph.problem_graph,
    "goal": svc_graph.goal_graph,
}


@router.get("", response_model=Envelope)
def graph(claims: UserClaims = Depends(get_current_user),
          type: str = Query("knowledge"), courseId: str = DEFAULT_COURSE, userId: str = ""):
    """三张图谱共用入口。

    type=knowledge 知识图谱（节点值=掌握度）
    type=problem   问题图谱（节点值=错误率，来自真实作答统计）
    type=goal      目标图谱（节点值=达成度，按关联知识点加权）

    userId 存在时按该学生视角计算，否则按当前用户所属班级计算。
    """
    cls = class_id_of(claims.user_id, claims.role)
    build = _BUILDERS.get(type, svc_graph.knowledge_graph)
    if type == "knowledge":
        return ok(build(student_id=userId or claims.user_id, class_id=cls, course_id=courseId))
    if type == "problem":
        return ok(build(class_id=cls, student_id=userId))
    return ok(build(student_id=userId or claims.user_id, class_id=cls))


@router.get("/kp/{kp_id}", response_model=Envelope)
def kp_detail(kp_id: str, claims: UserClaims = Depends(get_current_user)):
    """知识点详情：前测/后测掌握度、关联资源、题量、错题量。"""
    return ok(svc_graph.kp_detail(kp_id, student_id=claims.user_id,
                                  class_id=class_id_of(claims.user_id, claims.role)))


@router.get("/path", response_model=Envelope)
def learning_path(claims: UserClaims = Depends(get_current_user), courseId: str = DEFAULT_COURSE):
    """学习路径：节点状态（done/todo/warn/doing）由真实掌握度推导。"""
    return ok(svc_graph.learning_path(student_id=claims.user_id, course_id=courseId))
