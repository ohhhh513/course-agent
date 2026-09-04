# 课程智能体系统 · 后端（FastAPI）

与前端 `course-agent/` 配套的参考后端实现（技术栈 A：Python + FastAPI + SQLAlchemy）。

## 当前状态
- ✅ 已完成：统一信封、JWT 鉴权、CORS、真实库表（SQLAlchemy + Alembic）、契约测试、OpenAPI 导出、容器化。
- ✅ **真实化完成（非 AI）**：学生端（资源/掌握矩阵/能力雷达/成长/对比/预警/消息）、教师端（热力图/学生列表/个体画像/预警复核/私信）、练习闭环（组卷→判分→掌握度 EMA 更新→自动预警→报告→错题本）、题库（列表/编辑/审核/删除/导入）、知识点详情、课程、干预（列表/确认/忽略）均已读写真实关系表，`app/repo.py` 为统一数据访问层，并负责把数据库字段映射成前端 `api.js` 契约形状。
- ⏸️ **AI 部分暂缓**：`POST /ai/chat`（AI 答疑）与 `POST /question/gen`（AI 出题）本期**暂不实现**，接口已保留并返回 `available:false` + 明确提示「后期接入」。RAG / LLM 溯源相关表也未建，待 AI 模块启动时补齐。
- 🟡 **聚合大屏仍走快照**：驾驶舱（`*dashboard`）、图谱（`/graph` 列表与 `learningPath`）、归因（`/analysis/*`）、报告（`/report/*`）等重聚合端点暂由 `view_snapshots` 表承载（数据来自 `mock_data.json`，保证契约形状不变），后续由查询服务替换（接口形状不变）。

## 特性
- 统一响应信封 `{ code, message, data, traceId }`，与前端 `api.js` 契约一致。
- JWT 鉴权（`/auth/login`、`/auth/profile`、`/auth/reset-password`），401 自动包成信封。
- **真实数据库**：默认本地 SQLite（零配置），生产用 PostgreSQL（`DATABASE_URL` 切换）。
  - 关系表：`users` / `classes` / `courses` / `knowledge_points` / `questions` / `submissions` / `mastery_records` / `alerts` / `intervention_plans`。
  - 聚合视图快照表 `view_snapshots`：键对应前端 `mock_data.json` 顶层键，当前承载驾驶舱/图谱/归因/报告等重聚合端点，后续由查询服务替换（接口形状不变）。
- **种子数据来自前端 `assets/js/mock/data.js`**（经 `scripts/export_mock.cjs` 导出），保证后端 `data` 形状 = 前端单一真相源，前端 `mode='http'` 即可零改动对接。
- 登录/资料查询已接真实 `users` 表（DB 优先，演示账号兜底）。
- 内置契约测试 `tests/contract_check.py`：断言信封 + data 形状对齐 mock（含 AI 暂停态）。

## 目录
```
app/
  core/        配置 / 信封 / JWT 鉴权
  db/         SQLAlchemy 引擎/会话/模型（真实库表）
  data/        seed.py（读 view_snapshots 表，签名兼容旧 mock）
  routers/     各业务路由（auth/student/teacher/graph/ai/practice/analysis/question/intervention/report/course）
  main.py      装配 + 异常处理 + CORS
scripts/export_mock.cjs   从前端 mock 导出 JSON 种子
scripts/export_openapi.py 导出 openapi.json（联调/Postman 基准）
migrations/               Alembic 迁移（已生成 init schema）
tests/contract_check.py    契约测试
openapi.json               导出后的 OpenAPI 3.0 规范
```

## 快速开始
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
python scripts/export_mock.cjs        # 重新导出种子（前端 mock 更新后执行）
# 自动建表 + 灌种子（首次请求时 ensure_db 也会触发）
uvicorn app.main:app --reload --port 8000
curl http://localhost:8000/health
```

数据库初始化二选一：
- 开发：`python -c "from app.data.seed import ensure_db; ensure_db()"`（create_all + 灌种子）
- 生产：`alembic upgrade head`（版本化迁移）

## 前端对接
1. 把 `assets/js/api.js` 的 `config.mode` 改为 `'http'`，`baseURL` 保持 `/api/v1`。
2. 开发期用 Nginx / Vite 把 `/api` 反代到 `http://localhost:8000`，或在 `config.py` 放开 CORS。
3. 浏览器打开 `student.html` / `teacher.html`，用 `student/123456`、`teacher/123456` 登录。

## 契约测试
```bash
python tests/contract_check.py     # 47 项，全绿 ✅
```

## 容器化（可选）
```bash
docker compose up --build          # Postgres + Redis + backend，DATABASE_URL 自动指向 PG
```
本地开发不强制用容器：默认 SQLite 即可。

## AI 接口（暂缓说明）
| 接口 | 状态 | 返回 |
|---|---|---|
| `POST /ai/chat` | ⏸️ 后期接入 | `{ available:false, reason:"AI 答疑功能暂缓上线，后期接入（RAG 检索 + 严格溯源）。" }` |
| `POST /question/gen` | ⏸️ 后期接入 | `{ available:false, reason:"AI 出题功能暂缓上线，后期接入（LLM 结构化生成 + 溯源回填）。" }` |

其余 `/ai/*`（方法目录、会话历史、建议问题）、`/question/*`（配置、题库、审核、导入）为数据类接口，照常可用。

## 下一步（剩余工作）
- 为聚合端点编写真实查询服务（SQL 聚合 / 物化视图），逐步替换 `view_snapshots` 快照（接口形状不变）。
- 报告生成（`/report/generate`）、素材解析（`/question/materials`）接入 Celery（已预留 Redis）。
- 题目表补全 `isKey` / `correctRate` 等列并落库（当前为推导/近似）。
- AI 模块启动后：建 RAG 语料表 + 出题溯源表，实现 `/ai/chat`、`/question/gen` 两个暂缓接口。
- 详见 `docs/后端开发文档.md`（架构、模块映射、练习闭环、对接流程、迁移与演进）。
