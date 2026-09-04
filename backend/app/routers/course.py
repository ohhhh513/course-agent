from fastapi import APIRouter, Depends

from ..core.envelope import Envelope, ok
from ..core.security import UserClaims, get_current_user
from .. import repo

router = APIRouter(prefix="/course", tags=["course"])


@router.get("/{course_id}", response_model=Envelope)
def course(course_id: str, _: UserClaims = Depends(get_current_user)):
    return ok(repo.get_course(course_id))
