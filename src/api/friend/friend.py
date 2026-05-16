from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.api.deps import get_db, get_current_user
from src.models.auth.models import User
from src.models.base import api_res
from src.models.friend.schemas import (
    ContactSyncRequest,
    FriendAddRequest,
    FriendSearchByIdRequest,
    FriendUserInfo,
)
from src.services.friend.friend import FriendService

router = APIRouter(default_response_class=JSONResponse)


# ─── 직렬화 헬퍼 ───

def _build_friend_user_info(user: User, profile) -> dict:
    """User ORM + Profile ORM → FriendUserInfo dict 변환

    User와 Profile 두 테이블을 합쳐서 만들어야 하므로
    Pydantic model_validate() 대신 수동으로 조합한다.
    """
    return FriendUserInfo(
        uuid=user.uuid,
        kakao_id=user.kakao_id,
        name=user.name,
        nickname=profile.nickname if profile else "",
        profile_image_url=profile.profile_image_url if profile else None,
        status_message=profile.status_message if profile else "",
    ).model_dump()


def _serialize_friend(friend) -> dict:
    """Friend ORM → API 응답 dict 변환

    friend.friend_user (User) 와 friend.friend_user.profile (Profile) 은
    서비스 계층에서 joinedload로 미리 로드된 상태여야 한다.
    """
    profile = getattr(friend.friend_user, "profile", None)
    return {
        "id": friend.id,
        "friend_user": _build_friend_user_info(friend.friend_user, profile),
        "status": friend.status,
        "is_favorite": friend.is_favorite,
        "custom_name": friend.custom_name,
        "created_at": friend.created_at.isoformat(),
    }


# ─── Endpoints ───

@router.get("/list")
def get_friends(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """친구 목록 조회 — NORMAL 상태만, 즐겨찾기 우선 정렬"""
    friends = FriendService.get_friends(db, user)
    return api_res(success=True, data=[_serialize_friend(f) for f in friends])


@router.post("/search/id")
def search_by_id(
    body: FriendSearchByIdRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """카카오톡 ID로 유저 검색"""
    result = FriendService.search_by_kakao_id(db, body.kakao_id)

    if "error" in result:
        code, msg = result["error"]
        return api_res(success=False, error_code=code, error_msg=msg)

    return api_res(
        success=True,
        data={"user": _build_friend_user_info(result["user"], result["profile"])},
    )


@router.post("/add")
def add_friend(
    body: FriendAddRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """친구 추가 — 검색으로 얻은 UUID를 사용"""
    result = FriendService.add_friend(db, user, body.friend_uuid)

    if "error" in result:
        code, msg = result["error"]
        return api_res(success=False, error_code=code, error_msg=msg)

    return api_res(success=True, data={"friend": _serialize_friend(result["friend"])})


@router.post("/sync-contacts")
def sync_contacts(
    body: ContactSyncRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """연락처 동기화 — phone_hash 배열로 가입된 유저 중 아직 친구가 아닌 사람 반환"""
    result = FriendService.sync_contacts(db, user, body.phone_hashes)
    matched = [_build_friend_user_info(u, p) for u, p in result["matched"]]
    return api_res(success=True, data={"matched": matched})


@router.put("/{friend_id}/favorite")
def toggle_favorite(
    friend_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """즐겨찾기 토글 — True ↔ False 전환"""
    result = FriendService.toggle_favorite(db, user, friend_id)

    if "error" in result:
        code, msg = result["error"]
        return api_res(success=False, error_code=code, error_msg=msg)

    return api_res(success=True, data={"is_favorite": result["friend"].is_favorite})


@router.put("/{friend_id}/block")
def block_friend(
    friend_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """친구 차단 — NORMAL → BLOCKED 상태 전환, 친구 목록에서 사라짐"""
    result = FriendService.block_friend(db, user, friend_id)

    if "error" in result:
        code, msg = result["error"]
        return api_res(success=False, error_code=code, error_msg=msg)

    return api_res(success=True, data={"message": "차단되었습니다"})


@router.delete("/{friend_id}")
def delete_friend(
    friend_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """친구 삭제 — DB row 물리적 제거 (hard delete), 차단 상태도 삭제 가능"""
    result = FriendService.delete_friend(db, user, friend_id)

    if "error" in result:
        code, msg = result["error"]
        return api_res(success=False, error_code=code, error_msg=msg)

    return api_res(success=True, data={"message": "친구가 삭제되었습니다"})
