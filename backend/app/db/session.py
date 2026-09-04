"""数据库引擎与会话工厂。

默认读 core.config.DATABASE_URL：
  - sqlite:///./course_agent.db  （本地零配置）
  - postgresql+psycopg://...      （生产）
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..core.config import DATABASE_URL

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args, future=True, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def get_db():
    """FastAPI 依赖：请求级会话，用完自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
