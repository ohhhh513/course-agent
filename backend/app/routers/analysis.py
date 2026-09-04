"""学情分析：错因分布、高频错题、薄弱链条、归因结论。

归因结论（causes）**不使用 AI**，而是基于真实作答统计的规则引擎：
按优先级依次判定「前置知识缺失 / 计算失误 / 题意理解偏差 /
公式记忆错误 / 算法流程不清 / 概念混淆」，后期接入 LLM 时
只需替换 services.analysis.causes 的措辞生成层，判定输入不变。
"""
from fastapi import APIRouter, Depends

from ..core.envelope import Envelope, ok
from ..core.security import UserClaims, get_current_user
from ..services import analysis as svc_analysis
from ._ctx import class_id_of

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/errors", response_model=Envelope)
def errors(claims: UserClaims = Depends(get_current_user), chapter: str = "",
           kpId: str = "", timeRange: str = ""):
    """错因分析主面板：分布 / 高频错题 / 薄弱链 / 归因 / 共性VS个性。"""
    return ok(svc_analysis.error_analysis(class_id=class_id_of(claims.user_id, claims.role),
                                          chapter=chapter, time_range=timeRange, kp_id=kpId))


@router.get("/weak-chain", response_model=Envelope)
def weak_chain(claims: UserClaims = Depends(get_current_user), kpId: str = ""):
    """薄弱知识链：根 -> 中游 -> 叶，取掌握度最低的真实链路。"""
    return ok(svc_analysis.weak_chain(class_id=class_id_of(claims.user_id, claims.role),
                                      kp_id=kpId))


@router.get("/causes", response_model=Envelope)
def causes(claims: UserClaims = Depends(get_current_user)):
    return ok(svc_analysis.causes(class_id=class_id_of(claims.user_id, claims.role)))
