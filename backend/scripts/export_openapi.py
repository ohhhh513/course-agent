"""导出 OpenAPI 3.0 规范（联调基准 / Postman 可导入）。

运行：
  cd backend
  python scripts/export_openapi.py
生成：openapi.json（位于 backend/ 根目录）
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "openapi.json")

spec = app.openapi()
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(spec, f, ensure_ascii=False, indent=2)

print(f"OpenAPI 已导出 -> {OUT}")
print(f"  路径数: {len(spec.get('paths', {}))}")
print(f"  标题  : {spec.get('info', {}).get('title')} {spec.get('info', {}).get('version')}")
