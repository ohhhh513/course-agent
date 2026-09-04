FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 依赖安装（利用层缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 代码
COPY . .

EXPOSE 8000

# 入口：确保库表 + 灌种子（也可改走 alembic upgrade head），再起服务
CMD ["sh", "-c", "python -c 'from app.data.seed import ensure_db; ensure_db()' && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
