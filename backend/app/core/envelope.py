"""统一响应信封 + 业务异常。

前端 api.js 约定：所有响应包裹 { code, message, data, traceId }，
code===0 成功，前端读 data；code!==0 时用 message 直接 Toast 展示（中文）。
"""
import uuid
from typing import Any

from pydantic import BaseModel


class Envelope(BaseModel):
    code: int = 0
    message: str = "success"
    data: Any = None
    traceId: str | None = None


def _trace() -> str:
    return "svc-" + uuid.uuid4().hex[:8]


def ok(data: Any = None, message: str = "success") -> Envelope:
    return Envelope(code=0, message=message, data=data, traceId=_trace())


def fail(code: int, message: str, data: Any = None) -> Envelope:
    return Envelope(code=code, message=message, data=data, traceId=_trace())


class BizError(Exception):
    """业务异常：携带 code + message，由 main 的统一异常处理转成信封。"""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message
