"""练习 / 错题本（学生侧）真实端点。

练习闭环：组卷 -> 判分（与 questions.answer 比对）-> 掌握度 EMA 更新
-> 低于阈值自动生成 mastery_low 预警 -> 结算报告 -> 进入错题本。

前端在 submit/finish 时固定传 sessionId='cur'（忽略 create 返回的真实 id），
这里用进程内 `_current` 记录每位学生的「当前会话」，使判分与报告能关联到真实组卷。
"""
from fastapi import APIRouter, Depends

from ..core.envelope import Envelope, ok
from ..core.security import UserClaims, get_current_user
from .. import repo
from ..services import config_data as svc_config

router = APIRouter(prefix="/practice", tags=["practice"])

# student_id -> 最近一次创建的练习会话（弥补前端固定传 'cur'）
_current: dict[str, str] = {}


def _resolve_session(student_id: str, session_id: str | None) -> str:
    if session_id and session_id != "cur":
        return session_id
    return _current.get(student_id) or repo.latest_session_id(student_id) or ""


@router.get("/modes", response_model=Envelope)
def modes(claims: UserClaims = Depends(get_current_user)):
    """练习模式 + 各模式当前可选题量（按该生薄弱点 / 错题实时统计）。"""
    return ok(svc_config.practice_modes(claims.user_id))


@router.post("/sessions", response_model=Envelope)
def create_session(payload: dict, claims: UserClaims = Depends(get_current_user)):
    p = payload or {}
    mode = p.get("mode", "random")
    kp_ids = p.get("kpIds") or p.get("kpIds_json") or []
    count = int(p.get("count", 10) or 10)
    difficulty = int(p.get("difficulty", 1) or 1)
    res = repo.create_practice_session(claims.user_id, mode, kp_ids, count, difficulty)
    questions = repo.get_session_questions(res["sessionId"])
    _current[claims.user_id] = res["sessionId"]
    return ok({"sessionId": res["sessionId"], "mode": mode,
               "total": res["count"], "questions": questions})


@router.get("/sessions/{session_id}/questions", response_model=Envelope)
def get_questions(session_id: str, claims: UserClaims = Depends(get_current_user)):
    sid = _resolve_session(claims.user_id, session_id)
    return ok(repo.get_session_questions(sid))


@router.post("/answers", response_model=Envelope)
def submit_answer(payload: dict, claims: UserClaims = Depends(get_current_user)):
    p = payload or {}
    qid = p.get("qId")
    answer = p.get("answer")
    duration = int(p.get("durationSeconds", p.get("duration", 0) or 0) or 0)
    sid = _resolve_session(claims.user_id, p.get("sessionId"))
    return ok(repo.submit_answer(claims.user_id, sid, qid, answer, duration))


@router.post("/sessions/{session_id}/finish", response_model=Envelope)
def finish_session(session_id: str, claims: UserClaims = Depends(get_current_user)):
    sid = _resolve_session(claims.user_id, session_id)
    report = repo.finish_session(sid) or {}
    return ok(report)


@router.get("/wrong-book", response_model=Envelope)
def wrong_book(claims: UserClaims = Depends(get_current_user), mastered: str = "false",
               errorType: str = "", page: int = 1, size: int = 20):
    m = None if mastered == "all" else (mastered == "true")
    return ok(repo.wrong_book(claims.user_id, mastered=m, error_type=errorType,
                              page=page, size=size))


@router.get("/wrong-book/{q_id}/detail", response_model=Envelope)
def wrong_detail(q_id: str, claims: UserClaims = Depends(get_current_user)):
    return ok(repo.get_wrong_detail(claims.user_id, q_id))


@router.delete("/wrong-book/{q_id}", response_model=Envelope)
def remove_wrong(q_id: str, claims: UserClaims = Depends(get_current_user)):
    return ok(repo.delete_wrong(claims.user_id, q_id))
