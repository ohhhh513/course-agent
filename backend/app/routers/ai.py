"""AI 模块（答疑 / 会话 / 教学方法 / 推荐题）。

**约定：AI 相关能力本期暂缓上线。**
- /ai/chat            -> available:false（后期接 RAG + 严格溯源）
- /ai/sessions|messages -> 会话历史，属 AI 模块数据，保持只读快照
- /ai/methods         -> 教学方法，纯配置字典，转由 config_data 服务提供
- /ai/suggest-questions -> 推荐题，改由真实统计计算（非 AI，取薄弱点覆盖题）
"""
from fastapi import APIRouter, Depends

from ..core.envelope import Envelope, ok
from ..core.security import UserClaims, get_current_user
from ..data.seed import seed
from ..services import config_data as svc_config
from ..services import dashboard as svc_dashboard

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/methods", response_model=Envelope)
def methods(_: UserClaims = Depends(get_current_user)):
    return ok(svc_config.teaching_methods())


@router.get("/sessions", response_model=Envelope)
def sessions(_: UserClaims = Depends(get_current_user)):
    history = seed("chatHistory", [])
    return ok({"total": len(history), "list": history})


@router.get("/sessions/{session_id}/messages", response_model=Envelope)
def session_messages(session_id: str, _: UserClaims = Depends(get_current_user)):
    return ok(seed("chatMessages"))


@router.get("/suggest-questions", response_model=Envelope)
def suggest_questions(claims: UserClaims = Depends(get_current_user)):
    """首页推荐题：取该生薄弱知识点下未做过的题，真实计算。"""
    dash = svc_dashboard.student_dashboard(claims.user_id)
    return ok(dash.get("suggestedQuestions", []))


@router.post("/chat", response_model=Envelope)
def chat(payload: dict, _: UserClaims = Depends(get_current_user)):
    """AI 答疑：本期暂缓上线，后期接入（RAG + 严格溯源）。

    返回明确的可达状态，便于前端展示「功能待接入」而非静默失败。
    """
    return ok({
        "available": False,
        "reason": "AI 答疑功能暂缓上线，后期接入（RAG 检索 + 严格溯源）。",
        "question": (payload or {}).get("question", ""),
    })


@router.post("/feedback", response_model=Envelope)
def feedback(payload: dict, _: UserClaims = Depends(get_current_user)):
    return ok({"accepted": True})
