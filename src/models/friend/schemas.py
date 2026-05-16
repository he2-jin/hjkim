from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ─── Request Schemas ───

class FriendSearchByIdRequest(BaseModel):
    """카카오톡 ID로 유저 검색 요청"""
    kakao_id: str = Field(..., min_length=1, max_length=30, title="카카오톡 ID")


class FriendAddRequest(BaseModel):
    """친구 추가 요청 — 검색 후 얻은 UUID로 추가"""
    friend_uuid: str = Field(..., title="추가할 친구의 사용자 UUID")


class ContactSyncRequest(BaseModel):
    """연락처 동기화 요청 — raw 전화번호 대신 SHA-256 해시만 전송"""
    # min_length=1: 빈 배열 금지, max_length=500: 한 번에 최대 500개
    phone_hashes: list[str] = Field(..., min_length=1, max_length=500, title="전화번호 SHA-256 해시 목록")


# ─── Response Schemas ───

class FriendUserInfo(BaseModel):
    """친구의 사용자 정보 (User + Profile 조합)

    ORM 객체를 직접 변환하지 않고 API 핸들러에서 수동으로 조합해서 만든다.
    그래서 ConfigDict(from_attributes=True)를 쓰지 않아도 된다.
    """
    uuid: str = Field(..., title="사용자 UUID")
    kakao_id: Optional[str] = Field(None, title="카카오톡 ID")
    name: str = Field(..., title="이름")
    nickname: str = Field(..., title="닉네임")
    profile_image_url: Optional[str] = Field(None, title="프로필 이미지 URL")
    status_message: str = Field("", title="상태 메시지")


class FriendResponse(BaseModel):
    """친구 목록 항목 — GET /list, POST /add 응답에 사용"""
    id: int = Field(..., title="Friend ID (PUT /{id}/favorite, DELETE /{id}에 사용)")
    friend_user: FriendUserInfo = Field(..., title="친구의 사용자 정보")
    status: str = Field(..., title="관계 상태 (normal / blocked / hidden)")
    is_favorite: bool = Field(..., title="즐겨찾기 여부")
    custom_name: Optional[str] = Field(None, title="내가 설정한 별명")
    created_at: str = Field(..., title="친구 추가일시 (ISO 8601)")
