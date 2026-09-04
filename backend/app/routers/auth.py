from fastapi import APIRouter, Depends

from ..core.envelope import BizError, Envelope, ok
from ..core.security import DEMO_USERS, UserClaims, authenticate, create_token, get_current_user, public_user
from ..data.seed import seed

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Envelope)
def login(payload: dict):
    username = (payload or {}).get("username")
    password = (payload or {}).get("password")
    # role 仅用于前端预选标签；后端以账号库为准
    user = authenticate(username, password)
    token = create_token(user["userId"], user["role"])
    return ok({"token": token, "user": public_user(user)})


@router.get("/profile", response_model=Envelope)
def profile(claims: UserClaims = Depends(get_current_user)):
    # 优先真实用户表，回退演示账号
    try:
        from ..data.seed import get_user_by_id
        orm = get_user_by_id(claims.user_id)
        if orm is not None:
            return ok(orm.to_dict())
    except Exception:
        pass
    user = next((u for u in DEMO_USERS.values() if u["userId"] == claims.user_id), None)
    if not user:
        raise BizError(404, "用户不存在")
    return ok(public_user(user))


@router.post("/reset-password", response_model=Envelope)
def reset_password(payload: dict):
    """演示：校验账号 + 直接重置（真实环境应叠加验证码/安全问题）。"""
    username = (payload or {}).get("username")
    password = (payload or {}).get("password", "")
    if username not in DEMO_USERS:
        raise BizError(404, "账号不存在")
    if len(password) < 6:
        raise BizError(400, "新密码至少 6 位")
    DEMO_USERS[username]["password"] = password
    return ok({"ok": True})


@router.post("/logout", response_model=Envelope)
def logout(_: UserClaims = Depends(get_current_user)):
    # 演示：前端清会话即可；真实环境在此把 jti 进黑名单
    return ok({"ok": True})
