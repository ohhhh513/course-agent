"""服务层（Services）：聚合型端点的真实查询实现。

分层约定
--------
    Router（薄）  →  Services（厚，聚合计算）  →  repo / 真实表
                 →  repo（实体读写）

- `repo.py`：实体级读写（题目、作答、预警、干预…），返回规范数据。
- `services/*`：跨表聚合（驾驶舱、图谱、归因、报告…），返回**前端契约形状**。
- 两者都不写 HTTP 细节，路由只负责取参数、鉴权、包信封。
"""
from . import analysis, config_data, dashboard, graph, intervention, report  # noqa: F401

__all__ = ["analysis", "config_data", "dashboard", "graph", "intervention", "report"]
