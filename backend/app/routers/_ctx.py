"""路由层公共上下文。

只做一件事：把「当前登录用户」解析成后续 service 需要的维度参数
（班级 classId、学生/教师角色）。

放在这里而不是各个 router 里，是为了避免 8 个路由文件各写一份
「我是哪个班」的解析逻辑——那种重复正是之前快照回退滋生的温床。
"""
import json

from ..db import models as _m
from ..db.session import SessionLocal

DEFAULT_CLASS = "CL2301"
DEFAULT_COURSE = "C2026DS001"


def class_id_of(user_id: str, role: str = "") -> str:
    """解析当前用户所属班级。

    优先级：
      1. 教师 -> users.classes_json[0].classId
      2. 学生 -> students.classId
      3. 兜底 DEFAULT_CLASS
    """
    with SessionLocal() as s:
        if role == "teacher":
            u = s.get(_m.User, user_id)
            if u is not None and u.classes_json:
                try:
                    cs = json.loads(u.classes_json or "[]")
                    if cs and cs[0].get("classId"):
                        return cs[0]["classId"]
                except Exception:
                    pass
        st = s.get(_m.Student, user_id)
        if st is not None and st.classId:
            return st.classId
    return DEFAULT_CLASS


def is_teacher(role: str) -> bool:
    return role == "teacher"
