"""课程智能体系统 · 后端入口。

运行：
  cd backend
  uvicorn app.main:app --reload --port 8000
前端对接：把 assets/js/api.js 的 API.config.mode 改为 'http'，baseURL 保持 '/api/v1'，
并通过 Nginx/Vite 将 /api 反代到 http://localhost:8000（或开 CORS）。
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import API_PREFIX, CORS_ORIGINS
from .core.envelope import BizError, Envelope
from .routers import analysis, ai, auth, course, graph, intervention, practice, question, report, student, teacher

app = FastAPI(title="课程智能体系统 API", version="v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(BizError)
def _biz_handler(_: Request, exc: BizError):
    return JSONResponse(status_code=200, content=Envelope(code=exc.code, message=exc.message).model_dump())


@app.exception_handler(HTTPException)
def _http_handler(_: Request, exc: HTTPException):
    # 401/404/422 等统一包成信封，便于前端 Toast 直接展示 message
    return JSONResponse(status_code=exc.status_code, content=Envelope(code=exc.status_code, message=str(exc.detail)).model_dump())


@app.get("/health")
def health():
    return {"status": "ok"}


for _m in (auth, student, teacher, graph, ai, practice, analysis, question, intervention, report, course):
    app.include_router(_m.router, prefix=API_PREFIX)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
