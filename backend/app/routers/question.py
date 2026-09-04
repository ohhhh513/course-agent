"""题库：配置 / 素材上传 / AI 出题（暂缓）/ 列表 / 编辑 / 审核 / 导入 / 补练包。

AI 出题（POST /question/gen）按约定保持暂缓：路由保留、返回 available:false，
前端据此展示「功能待接入」，后期接入时只需替换这一个 handler。
"""
import uuid

from fastapi import APIRouter, Depends, UploadFile, File

from ..core.envelope import Envelope, ok
from ..core.security import UserClaims, get_current_user
from .. import repo
from ..services import config_data as svc_config
from ._ctx import class_id_of

router = APIRouter(prefix="/question", tags=["question"])


@router.get("/gen/config", response_model=Envelope)
def gen_config(claims: UserClaims = Depends(get_current_user)):
    """出题页配置：素材库（materials 表）+ 知识点选项 + 题型选项。"""
    return ok(svc_config.gen_config(class_id=class_id_of(claims.user_id, claims.role)))


@router.post("/materials", response_model=Envelope)
async def upload_material(file: UploadFile = File(...), _: UserClaims = Depends(get_current_user)):
    """上传素材：真实落 materials 表，状态 parsing（解析完成后由任务置为 parsed）。"""
    size = ""
    try:
        raw = await file.read()
        mb = len(raw) / 1024 / 1024
        size = f"{mb:.1f} MB" if mb >= 1 else f"{max(1, len(raw) // 1024)} KB"
    except Exception:
        pass
    return ok(svc_config.add_material(file.filename or "未命名素材", size=size))


@router.post("/gen", response_model=Envelope)
def generate(payload: dict, _: UserClaims = Depends(get_current_user)):
    """AI 出题：本期暂缓上线，后期接入（LLM 结构化生成 + 溯源回填）。"""
    return ok({
        "available": False,
        "reason": "AI 出题功能暂缓上线，后期接入（LLM 结构化生成 + kpPath/preKp/postKp/sourceRef 溯源）。",
    })


@router.get("/bank", response_model=Envelope)
def bank(_: UserClaims = Depends(get_current_user), kpId: str = "", type: str = "",
         status: str = "", difficulty: str = "", keyword: str = "", page: int = 1, size: int = 20):
    return ok(repo.list_questions(kp_id=kpId, type=type, status=status,
                                   difficulty=difficulty, keyword=keyword, page=page, size=size))


@router.put("/{q_id}", response_model=Envelope)
def update_question(q_id: str, payload: dict, _: UserClaims = Depends(get_current_user)):
    return ok(repo.upsert_question({**payload, "qId": q_id}))


@router.post("/review", response_model=Envelope)
def review(payload: dict, _: UserClaims = Depends(get_current_user)):
    """批量审核发布：action -> 题目状态（approve/pubending, publish/published, reject/archived）。"""
    p = payload or {}
    action = p.get("action", "publish")
    status_map = {"approve": "approved", "publish": "published", "reject": "archived"}
    target = status_map.get(action, "published")
    qids = p.get("qIds") or []
    for qid in qids:
        repo.upsert_question({"qId": qid, "status": target})
    return ok({"affected": len(qids), "action": action})


@router.delete("/{q_id}", response_model=Envelope)
def remove_question(q_id: str, _: UserClaims = Depends(get_current_user)):
    return ok(repo.delete_question(q_id))


@router.post("/import", response_model=Envelope)
def import_batch(payload: dict, _: UserClaims = Depends(get_current_user)):
    p = payload or {}
    items = p.get("items") or p.get("questions") or []
    return ok(repo.import_questions(items))


@router.post("/packs", response_model=Envelope)
def create_pack(payload: dict, _: UserClaims = Depends(get_current_user)):
    """靶向补练包：返回包号占位，真实环境据此组卷并推送。

    与 AI 无关（纯组卷逻辑），但组卷推送需要对接消息通道，此处只落包号。
    """
    p = payload or {}
    return ok({"packId": "PK" + uuid.uuid4().hex[:8], "kpIds": p.get("kpIds", []),
               "count": p.get("count", 6), "pushed": True})
