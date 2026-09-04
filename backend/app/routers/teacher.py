"""教师端：班级概览、热力图、学生列表、学情档案、预警处置、私信。

所有聚合都基于真实表计算：
  - 班级概览 -> services.dashboard.teacher_dashboard
  - 热力图 / 学生列表 / 档案 / 预警 -> repo（实体级 + 班级分析）
"""
from fastapi import APIRouter, Depends

from ..core.envelope import Envelope, ok
from ..core.security import UserClaims, get_current_user
from .. import repo
from ..services import dashboard as svc_dashboard
from ._ctx import class_id_of

router = APIRouter(prefix="/teacher", tags=["teacher"])


@router.get("/dashboard", response_model=Envelope)
def dashboard(claims: UserClaims = Depends(get_current_user)):
    """教师首页：班级概览（含近 7 日环比）/ 实时动态 / 待办 / 薄弱知识点排行。"""
    return ok(svc_dashboard.teacher_dashboard(class_id_of(claims.user_id, claims.role)))


@router.get("/heatmap", response_model=Envelope)
def heatmap(claims: UserClaims = Depends(get_current_user), dimension: str = "week"):
    """班级 × 知识点掌握度热力图（轴为展示名，值由 mastery_records 实算）。"""
    return ok(repo.teacher_heatmap(class_id_of(claims.user_id, claims.role), dimension))


@router.get("/students", response_model=Envelope)
def students(claims: UserClaims = Depends(get_current_user), alertLevel: str = "all",
             keyword: str = "", sortBy: str = "mastery", page: int = 1):
    return ok(repo.teacher_students(class_id_of(claims.user_id, claims.role),
                                    alert_level=alertLevel, keyword=keyword,
                                    sort_by=sortBy, page=page))


@router.get("/students/{user_id}/profile", response_model=Envelope)
def student_profile(user_id: str, _: UserClaims = Depends(get_current_user)):
    """单个学生的学情档案：指标 / 学习时段分布 / 活跃趋势 / 知识点明细 / 错题明细。"""
    return ok(repo.student_profile(user_id))


@router.get("/alerts", response_model=Envelope)
def alerts(claims: UserClaims = Depends(get_current_user), level: str = "all",
           status: str = "all", type: str = "", kpId: str = "", page: int = 1):
    return ok(repo.teacher_alerts(class_id_of(claims.user_id, claims.role), level=level,
                                  status=status, type=type, kp_id=kpId, page=page))


@router.put("/alerts/{alert_id}/review", response_model=Envelope)
def review_alert(alert_id: str, payload: dict, _: UserClaims = Depends(get_current_user)):
    action = (payload or {}).get("action", "confirm")
    return ok(repo.review_alert(alert_id, action, (payload or {}).get("note", "")))


@router.post("/messages", response_model=Envelope)
def send_message(payload: dict, claims: UserClaims = Depends(get_current_user)):
    p = payload or {}
    uid = p.get("userId", "")
    if not uid:
        from ..core.envelope import BizError
        raise BizError(400, "缺少收件人 userId")
    repo.send_message(uid, p.get("sender", "教师"), p.get("content", ""),
                      title=p.get("title", "教师私信"))
    return ok({"ok": True, "to": uid})
