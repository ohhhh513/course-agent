"""鉴权：JWT 签发/校验 + 当前用户依赖。

演示账号（真实环境应查数据库）：
  student / 123456  -> 学生陈思远
  teacher / 123456  -> 教师李文博
用户字段名严格对齐《鉴权与会话方案.md §5》。
"""
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Header, HTTPException

from .config import JWT_ALGO, JWT_EXPIRE_MINUTES, JWT_SECRET
from .envelope import BizError

DEMO_USERS: dict[str, dict] = {
    "student": {
        "userId": "S20260317", "name": "陈思远", "role": "student",
        "password": "123456", "avatarChar": "陈", "org": "计算机 2301 班",
        "title": "", "dept": "", "classes": [],
    },
    "teacher": {
        "userId": "T100286", "name": "李文博", "role": "teacher",
        "password": "123456", "avatarChar": "李", "title": "副教授",
        "dept": "计算机科学与技术学院",
        "classes": [{"classId": "CL2301", "name": "计算机 2301 班", "studentCount": 42}],
    },
}


def create_token(user_id: str, role: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "role": role, "exp": exp}, JWT_SECRET, algorithm=JWT_ALGO)


def public_user(u: dict) -> dict:
    return {k: v for k, v in u.items() if k != "password"}


class UserClaims:
    def __init__(self, user_id: str | None, role: str | None):
        self.user_id = user_id
        self.role = role


def get_current_user(authorization: str = Header(None)) -> UserClaims:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录或令牌缺失")
    token = authorization[7:]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录已过期")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="令牌无效")
    return UserClaims(payload.get("sub"), payload.get("role"))


def authenticate(username: str, password: str) -> dict:
    """返回用户 dict 或抛出 BizError。

    优先查真实用户表（users）；表为空或异常时回退到内置演示账号，保证本地零配置可跑。
    """
    try:
        from ..data.seed import ensure_db, get_user_by_username
        ensure_db()
        orm = get_user_by_username(username)
        if orm is not None and orm.password_hash == password:
            return orm.to_dict()
    except Exception:
        # 任何数据库异常都不应阻塞登录，回退演示账号
        pass
    user = DEMO_USERS.get(username)
    if not user:
        raise BizError(404, "账号不存在")
    if user["password"] != password:
        raise BizError(401, "密码错误，请重试")
    return user
