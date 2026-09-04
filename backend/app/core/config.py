"""运行配置（从环境变量读取，提供默认值，便于本地零配置启动）。"""
import os

# JWT 签名密钥：生产环境务必通过环境变量注入强随机值
# 默认仅用于本地开发（≥32 字节）；生产环境务必通过环境变量注入强随机值
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me-please-rotate-in-prod-32")
JWT_ALGO = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

# CORS：开发期可用 *；生产环境写成前端域名逗号分隔
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

# 服务基础路径（与前端 api.js 的 baseURL 对应）
API_PREFIX = "/api/v1"

# 数据库：默认本地 SQLite（零配置即可跑）；生产环境用环境变量注入 PostgreSQL
# 例：postgresql+psycopg://user:pass@host:5432/course_agent
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./course_agent.db")
