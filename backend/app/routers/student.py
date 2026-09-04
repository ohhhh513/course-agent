"""学生端：概览、掌握度、能力、成长、对比、预警、消息。

数据来源全部走真实表（repo 实体读写 + services 聚合）：
  - 实体 / 单学生分析 -> repo
  - 跨模块聚合（概览大屏）-> services.dashboard
"""
from fastapi import APIRouter, Depends

from ..core.envelope import Envelope, ok
from ..core.security import UserClaims, get_current_user
from .. import repo
from ..services import dashboard as svc_dashboard

router = APIRouter(prefix="/student", tags=["student"])


@router.get("/dashboard", response_model=Envelope)
def dashboard(claims: UserClaims = Depends(get_current_user)):
    """学生首页：连续学习 / 核心指标 / 待办 / 薄弱点 / 推荐题 / 最近动态。"""
    return ok(svc_dashboard.student_dashboard(claims.user_id))


@router.get("/resources", response_model=Envelope)
def resources(_: UserClaims = Depends(get_current_user), type: str = "all", kpId: str = "",
              keyword: str = "", page: int = 1, size: int = 12):
    return ok(repo.list_resources(type=type, kp_id=kpId, keyword=keyword, page=page, size=size))


@router.get("/mastery/matrix", response_model=Envelope)
def mastery_matrix(claims: UserClaims = Depends(get_current_user)):
    """按章节分组的掌握度矩阵（数组形态，供前端直接渲染）。"""
    return ok(repo.mastery_matrix(claims.user_id))


@router.get("/ability/radar", response_model=Envelope)
def ability_radar(claims: UserClaims = Depends(get_current_user)):
    """六维能力雷达：我的 / 班级均值 / 目标基线三条序列。"""
    return ok(repo.ability_radar(claims.user_id))


@router.get("/growth", response_model=Envelope)
def growth(claims: UserClaims = Depends(get_current_user), dimension: str = "week"):
    """成长轨迹：week / month / semester。"""
    return ok(repo.growth_track(claims.user_id, dimension))


@router.get("/compare", response_model=Envelope)
def compare(claims: UserClaims = Depends(get_current_user)):
    """我与班级的对比：排名、百分位、各项指标差值。"""
    return ok(repo.class_compare(claims.user_id))


@router.get("/alerts", response_model=Envelope)
def alerts(claims: UserClaims = Depends(get_current_user), level: str = "all", status: str = "open"):
    return ok(repo.student_alerts(claims.user_id, level=level, status=status))


@router.put("/alerts/{alert_id}/read", response_model=Envelope)
def read_alert(alert_id: str, _: UserClaims = Depends(get_current_user)):
    return ok(repo.read_alert(alert_id))


@router.get("/messages", response_model=Envelope)
def messages(claims: UserClaims = Depends(get_current_user)):
    return ok(repo.list_messages(claims.user_id))
