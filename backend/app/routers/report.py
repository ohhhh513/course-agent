"""学情报告：列表 / 生成 / 详情 / 导出。

报告正文由 services.report 依据真实统计（掌握度、正确率、错题分布、
预警、干预）生成 6 个章节并**落库**，因此报告可复现、可回溯——
不是每次请求都重新编一份的快照。
"""
from fastapi import APIRouter, Depends

from ..core.envelope import Envelope, ok
from ..core.security import UserClaims, get_current_user
from ..services import report as svc_report
from ._ctx import class_id_of

router = APIRouter(prefix="/report", tags=["report"])


@router.get("/list", response_model=Envelope)
def list_reports(claims: UserClaims = Depends(get_current_user), page: int = 1):
    rows = svc_report.list_reports(class_id=class_id_of(claims.user_id, claims.role))
    size = 10
    start = max(0, (page - 1) * size)
    return ok({"total": len(rows), "list": rows[start:start + size]})


@router.post("/generate", response_model=Envelope)
def generate(payload: dict, claims: UserClaims = Depends(get_current_user)):
    """按班级 / 章节 / 时间区间生成报告（同步返回，落库后可反复查看）。"""
    return ok(svc_report.generate_report(payload or {}, creator=claims.user_id))


@router.get("/{report_id}", response_model=Envelope)
def detail(report_id: str, _: UserClaims = Depends(get_current_user)):
    """报告详情；reportId 不存在时回退到最近一份，保证前端直接访问不 404。"""
    return ok(svc_report.get_report(report_id))


@router.post("/{report_id}/export", response_model=Envelope)
def export(report_id: str, payload: dict, _: UserClaims = Depends(get_current_user)):
    fmt = (payload or {}).get("format", "pdf")
    return ok({"url": f"/exports/{report_id}.{fmt}", "format": fmt})
