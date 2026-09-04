"""真实关系表（替代原 mock seed）。

设计原则
--------
1. **实体表**：用户/班级/课程/知识点/题目/作答/掌握度/预警/干预/学生档案/资源/消息，
   全部真实落库，写操作直接持久化（练习判分 -> 掌握度 -> 预警 -> 报告闭环）。
2. **图谱表** `graph_nodes` / `graph_links`：承载知识图谱、问题图谱、目标图谱的
   结构与静态属性；**动态属性（掌握率 / 错误率 / 达成度）在查询时由真实表计算覆盖**，
   保证图谱永远反映当前学情，而不是一份写死的快照。
3. **配置/素材表** `materials` / `strategy_templates`：素材库与策略库可增删，真实持久化。
4. **报表表** `reports`：一键生成的报告落库，可归档、可翻历史。
5. **学习日历表** `study_days`：驾驶舱「连续学习天数 / 贡献图」的真实数据源
   （种子来自 mock，之后由练习与学习行为追加）。
6. **AI 相关表**（RAG 语料、出题溯源）本期暂缓，待 AI 模块接入时再补。

> `view_snapshots` 仅作为**历史兼容的兜底**，v1 中所有端点均已改走真实表，
> 新代码不要再依赖它。
"""
import json

from sqlalchemy import (
    Boolean, Float, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class User(Base):
    __tablename__ = "users"

    userId: Mapped[str] = mapped_column(String(32), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), default="")
    role: Mapped[str] = mapped_column(String(16), default="student")
    name: Mapped[str] = mapped_column(String(64), default="")
    avatar_char: Mapped[str] = mapped_column(String(4), default="")
    avatar_color: Mapped[str] = mapped_column(String(128), default="")
    org: Mapped[str] = mapped_column(String(128), default="")
    title: Mapped[str] = mapped_column(String(64), default="")
    dept: Mapped[str] = mapped_column(String(128), default="")
    classes_json: Mapped[str] = mapped_column(Text, default="[]")

    def to_dict(self) -> dict:
        """字段与前端账号对象一致（auth.js 的 SEED 账号形状）。"""
        return {
            "userId": self.userId,
            "username": self.username,
            "role": self.role,
            "name": self.name,
            "org": self.org,
            "avatarChar": self.avatar_char,
            "avatarColor": self.avatar_color,
            "title": self.title,
            "dept": self.dept,
            "classes": json.loads(self.classes_json or "[]"),
        }


class ClassGroup(Base):
    __tablename__ = "classes"

    classId: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    studentCount: Mapped[int] = mapped_column(Integer, default=0)
    grade: Mapped[str] = mapped_column(String(32), default="")
    courseId: Mapped[str] = mapped_column(String(32), default="")


class Course(Base):
    __tablename__ = "courses"

    courseId: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    code: Mapped[str] = mapped_column(String(32), default="")
    teacherId: Mapped[str] = mapped_column(String(32), default="")
    term: Mapped[str] = mapped_column(String(32), default="")
    credit: Mapped[int] = mapped_column(Integer, default=0)


class KnowledgePoint(Base):
    """知识点：结构（前后置）+ 静态属性（章/难度/学时/重难点）。

    动态属性（掌握率）来自 mastery_records，查询时覆盖图谱节点。
    """

    __tablename__ = "knowledge_points"

    kpId: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    parentId: Mapped[str] = mapped_column(String(32), default="")
    courseId: Mapped[str] = mapped_column(String(32), default="")
    chapter: Mapped[int] = mapped_column(Integer, default=0)
    chapterName: Mapped[str] = mapped_column(String(64), default="")
    orderNo: Mapped[int] = mapped_column(Integer, default=0)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    isKey: Mapped[bool] = mapped_column(Boolean, default=False)
    hours: Mapped[int] = mapped_column(Integer, default=0)
    type: Mapped[str] = mapped_column(String(16), default="")
    status: Mapped[str] = mapped_column(String(16), default="")
    desc: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    preKp: Mapped[str] = mapped_column(Text, default="[]")
    postKp: Mapped[str] = mapped_column(Text, default="[]")


class Question(Base):
    __tablename__ = "questions"

    qId: Mapped[str] = mapped_column(String(32), primary_key=True)
    kpId: Mapped[str] = mapped_column(String(32), default="", index=True)
    type: Mapped[str] = mapped_column(String(16), default="")
    stem: Mapped[str] = mapped_column(Text, default="")
    options_json: Mapped[str] = mapped_column(Text, default="[]")
    answer: Mapped[str] = mapped_column(Text, default="")
    analysis: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(16), default="pending")
    isKey: Mapped[bool] = mapped_column(Boolean, default=False)
    useCount: Mapped[int] = mapped_column(Integer, default=0)
    createdAt: Mapped[str] = mapped_column(String(32), default="")


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    studentId: Mapped[str] = mapped_column(String(32), index=True, default="")
    qId: Mapped[str] = mapped_column(String(32), index=True, default="")
    answer: Mapped[str] = mapped_column(Text, default="")
    correct: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    ts: Mapped[str] = mapped_column(String(32), default="")
    duration: Mapped[int] = mapped_column(Integer, default=0)
    mastered: Mapped[bool] = mapped_column(Boolean, default=False)
    errorType: Mapped[str] = mapped_column(String(32), default="")


class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sessionId: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    studentId: Mapped[str] = mapped_column(String(32), index=True, default="")
    mode: Mapped[str] = mapped_column(String(16), default="random")
    kpIds_json: Mapped[str] = mapped_column(Text, default="[]")
    qIds_json: Mapped[str] = mapped_column(Text, default="[]")
    count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="open")
    ts: Mapped[str] = mapped_column(String(32), default="")


class MasteryRecord(Base):
    __tablename__ = "mastery_records"
    __table_args__ = (UniqueConstraint("studentId", "kpId", name="uq_mastery_stu_kp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    studentId: Mapped[str] = mapped_column(String(32), index=True, default="")
    kpId: Mapped[str] = mapped_column(String(32), index=True, default="")
    mastery: Mapped[float] = mapped_column(Float, default=0.0)
    correctRate: Mapped[float] = mapped_column(Float, default=0.0)
    completion: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16), default="")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alertId: Mapped[str] = mapped_column(String(32), index=True, default="")
    studentId: Mapped[str] = mapped_column(String(32), index=True, default="")
    studentName: Mapped[str] = mapped_column(String(64), default="")
    type: Mapped[str] = mapped_column(String(32), default="")
    level: Mapped[str] = mapped_column(String(16), default="info")
    title: Mapped[str] = mapped_column(String(128), default="")
    desc: Mapped[str] = mapped_column(Text, default="")
    trigger: Mapped[str] = mapped_column(Text, default="")
    kpId: Mapped[str] = mapped_column(String(32), default="")
    kp: Mapped[str] = mapped_column(String(128), default="")
    detail_json: Mapped[str] = mapped_column(Text, default="{}")
    suggestions_json: Mapped[str] = mapped_column(Text, default="[]")
    trend_json: Mapped[str] = mapped_column(Text, default="[]")
    createdAt: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(16), default="open")
    read: Mapped[bool] = mapped_column(Boolean, default=False)


class InterventionPlan(Base):
    __tablename__ = "intervention_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    planId: Mapped[str] = mapped_column(String(32), index=True, default="")
    studentId: Mapped[str] = mapped_column(String(32), index=True, default="")
    teacherId: Mapped[str] = mapped_column(String(32), default="")
    type: Mapped[str] = mapped_column(String(32), default="")
    scope: Mapped[str] = mapped_column(String(32), default="common")
    level: Mapped[str] = mapped_column(String(16), default="warn")
    alertId: Mapped[str] = mapped_column(String(32), default="")
    title: Mapped[str] = mapped_column(String(128), default="")
    target: Mapped[str] = mapped_column(String(256), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="[]")      # steps
    resources_json: Mapped[str] = mapped_column(Text, default="[]")
    expectEffect: Mapped[str] = mapped_column(Text, default="")
    packId: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    createdAt: Mapped[str] = mapped_column(String(32), default="")


class Student(Base):
    __tablename__ = "students"

    userId: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), default="")
    no: Mapped[str] = mapped_column(String(32), default="")
    avatar: Mapped[str] = mapped_column(String(8), default="")
    classId: Mapped[str] = mapped_column(String(32), index=True, default="")
    className: Mapped[str] = mapped_column(String(128), default="")
    completionRate: Mapped[float] = mapped_column(Float, default=0.0)
    masteryRate: Mapped[float] = mapped_column(Float, default=0.0)
    goalAchieveRate: Mapped[float] = mapped_column(Float, default=0.0)
    activeRate: Mapped[float] = mapped_column(Float, default=0.0)
    alertLevel: Mapped[str] = mapped_column(String(16), default="green")
    alertCount: Mapped[int] = mapped_column(Integer, default=0)
    lastActive: Mapped[str] = mapped_column(String(32), default="")
    studyMinutes: Mapped[int] = mapped_column(Integer, default=0)
    rank: Mapped[int] = mapped_column(Integer, default=0)


class Resource(Base):
    __tablename__ = "resources"

    resId: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(256), default="")
    type: Mapped[str] = mapped_column(String(16), default="video")
    kp: Mapped[str] = mapped_column(String(128), default="")
    kpId: Mapped[str] = mapped_column(String(32), index=True, default="")
    source: Mapped[str] = mapped_column(String(128), default="")
    views: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    duration: Mapped[str] = mapped_column(String(16), default="")   # "22:10"
    pages: Mapped[int] = mapped_column(Integer, default=0)
    count: Mapped[int] = mapped_column(Integer, default=0)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    msgId: Mapped[str] = mapped_column(String(32), default="")
    userId: Mapped[str] = mapped_column(String(32), index=True, default="")
    sender: Mapped[str] = mapped_column(String(64), default="")
    to: Mapped[str] = mapped_column(String(64), default="")
    title: Mapped[str] = mapped_column(String(128), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    time: Mapped[str] = mapped_column(String(32), default="")
    read: Mapped[bool] = mapped_column(Boolean, default=False)


class StudyDay(Base):
    """学习日历：驾驶舱贡献图 / 连续学习天数的真实数据源。"""

    __tablename__ = "study_days"
    __table_args__ = (UniqueConstraint("studentId", "day", name="uq_studyday"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    studentId: Mapped[str] = mapped_column(String(32), index=True, default="")
    day: Mapped[str] = mapped_column(String(16), default="")   # YYYY-MM-DD
    minutes: Mapped[int] = mapped_column(Integer, default=0)
    questions: Mapped[int] = mapped_column(Integer, default=0)


class Material(Base):
    """出题素材库（上传 -> 解析 -> 挂载知识点）。"""

    __tablename__ = "materials"

    fileId: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), default="")
    size: Mapped[str] = mapped_column(String(32), default="")
    type: Mapped[str] = mapped_column(String(16), default="doc")
    status: Mapped[str] = mapped_column(String(16), default="parsed")
    kpCount: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[int] = mapped_column(Integer, default=100)
    uploadedAt: Mapped[str] = mapped_column(String(32), default="")


class StrategyTemplate(Base):
    __tablename__ = "strategy_templates"

    tplId: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    scene: Mapped[str] = mapped_column(String(64), default="")
    desc: Mapped[str] = mapped_column(Text, default="")
    useCount: Mapped[int] = mapped_column(Integer, default=0)
    successRate: Mapped[int] = mapped_column(Integer, default=0)
    avgLift: Mapped[float] = mapped_column(Float, default=0.0)
    tags_json: Mapped[str] = mapped_column(Text, default="[]")


class Report(Base):
    """学情分析报告：一键生成后落库，支持历史归档与详情回看。"""

    __tablename__ = "reports"

    reportId: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(256), default="")
    scope: Mapped[str] = mapped_column(String(64), default="")
    period: Mapped[str] = mapped_column(String(64), default="")
    createdAt: Mapped[str] = mapped_column(String(32), default="")
    creator: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="ready")
    pages: Mapped[int] = mapped_column(Integer, default=0)
    classId: Mapped[str] = mapped_column(String(32), default="")
    meta_json: Mapped[str] = mapped_column(Text, default="{}")
    sections_json: Mapped[str] = mapped_column(Text, default="[]")


class GraphNode(Base):
    """图谱节点：graphType ∈ {knowledge, problem, goal}。

    payload_json 保存静态属性（章/难度/学时/权重等）；掌握率、错误率、达成度
    等动态值由 services/graph.py 在查询时用真实表覆盖。
    """

    __tablename__ = "graph_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    graphType: Mapped[str] = mapped_column(String(16), index=True, default="")
    nodeId: Mapped[str] = mapped_column(String(32), default="")
    name: Mapped[str] = mapped_column(String(256), default="")
    category: Mapped[int] = mapped_column(Integer, default=0)
    orderNo: Mapped[int] = mapped_column(Integer, default=0)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")


class GraphLink(Base):
    __tablename__ = "graph_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    graphType: Mapped[str] = mapped_column(String(16), index=True, default="")
    sourceId: Mapped[str] = mapped_column(String(32), default="")
    targetId: Mapped[str] = mapped_column(String(32), default="")
    relation: Mapped[str] = mapped_column(String(16), default="pre")


class ViewSnapshot(Base):
    """历史兼容：旧版聚合快照。v1 全部端点已改走真实表，仅保留不再新增依赖。"""

    __tablename__ = "view_snapshots"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
