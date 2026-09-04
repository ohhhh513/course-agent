"""教学干预：方案列表 / 确认 / 驳回 / 效果追踪 / 策略模板。

干预效果（effect）不再是写死的快照：它以方案创建时间为分界，
按 6 个时间窗口计算「干预组 vs 对照组」的真实正确率曲线与净提升。
"""
from fastapi import APIRouter, Depends

from ..core.envelope import Envelope, ok
from ..core.security import UserClaims, get_current_user
from .. import repo
from ..services import intervention as svc_intervention
from ._ctx import class_id_of

router = APIRouter(prefix="/intervention", tags=["intervention"])


@router.get("/list", response_model=Envelope)
def list_interventions(claims: UserClaims = Depends(get_current_user), classId: str = "",
                       status: str = "all", scope: str = "all"):
    return ok(repo.list_interventions(classId or class_id_of(claims.user_id, claims.role),
                                      status=status, scope=scope))


@router.post("/{iv_id}/confirm", response_model=Envelope)
def confirm(iv_id: str, payload: dict, _: UserClaims = Depends(get_current_user)):
    p = payload or {}
    return ok(repo.confirm_intervention(iv_id, steps=p.get("steps"),
                                        resources=p.get("resources"), note=p.get("note", "")))


@router.post("/{iv_id}/reject", response_model=Envelope)
def reject(iv_id: str, _: UserClaims = Depends(get_current_user)):
    return ok(repo.reject_intervention(iv_id))


@router.get("/{iv_id}/effect", response_model=Envelope)
def effect(iv_id: str, claims: UserClaims = Depends(get_current_user)):
    """干预效果：干预组 / 对照组正确率曲线 + 净提升（真实作答统计）。"""
    return ok(svc_intervention.intervention_effect(iv_id, class_id=class_id_of(claims.user_id, claims.role)))


@router.get("/templates", response_model=Envelope)
def templates(_: UserClaims = Depends(get_current_user), scene: str = "", keyword: str = ""):
    return ok(svc_intervention.list_templates(scene=scene, keyword=keyword))


@router.post("/templates", response_model=Envelope)
def save_template(payload: dict, _: UserClaims = Depends(get_current_user)):
    """策略沉淀：真实落 strategy_templates 表。"""
    return ok(svc_intervention.save_template(payload or {}))
