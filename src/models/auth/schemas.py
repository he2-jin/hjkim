from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ─── Request Schemas ───

class RegisterRequest(BaseModel):
    """회원가입 요청"""
    kakao_id: str = Field(..., min_length=4, max_length=30, title="카카오톡 ID")
    phone: str = Field(..., min_length=10, max_length=20, title="전화번호")
    password: str = Field(..., min_length=8, max_length=100, title="비밀번호")
    name: str = Field(..., min_length=1, max_length=30, title="이름")
    nickname: str = Field(..., min_length=1, max_length=20, title="닉네임")
    email: Optional[str] = Field(None, max_length=100, title="이메일")
    device_type: str = Field("web", title="기기 타입")
    device_name: Optional[str] = Field(None, max_length=100, title="기기 이름")

    @field_validator("kakao_id")
    @classmethod
    def validate_kakao_id(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError("카카오톡 ID는 영문, 숫자만 가능합니다")
        return v.lower()


class LoginRequest(BaseModel):
    """로그인 요청"""
    kakao_id: str = Field(..., title="카카오톡 ID")
    password: str = Field(..., title="비밀번호")
    device_type: str = Field("web", title="기기 타입")
    device_name: Optional[str] = Field(None, title="기기 이름")


class TokenRefreshRequest(BaseModel):
    """토큰 갱신 요청"""
    refresh_token: str = Field(..., title="Refresh Token")


class PasswordChangeRequest(BaseModel):
    """비밀번호 변경 요청"""
    current_password: str = Field(..., title="현재 비밀번호")
    new_password: str = Field(..., min_length=8, max_length=100, title="새 비밀번호")


# ─── Response Schemas ───

class TokenResponse(BaseModel):
    """토큰 응답"""
    access_token: str = Field(..., title="Access Token")
    refresh_token: str = Field(..., title="Refresh Token")
    token_type: str = Field("bearer", title="토큰 타입")


class UserResponse(BaseModel):
    """사용자 응답"""
    model_config = ConfigDict(from_attributes=True)

    uuid: str = Field(..., title="사용자 UUID")
    kakao_id: Optional[str] = Field(None, title="카카오톡 ID")
    name: str = Field(..., title="이름")
    phone: str = Field(..., title="전화번호")
    email: Optional[str] = Field(None, title="이메일")
    status: str = Field(..., title="상태")
    created_at: datetime = Field(..., title="가입일시")


class ProfileResponse(BaseModel):
    """프로필 응답"""
    model_config = ConfigDict(from_attributes=True)

    nickname: str = Field(..., title="닉네임")
    status_message: str = Field("", title="상태 메시지")
    profile_image_url: Optional[str] = Field(None, title="프로필 이미지")
    background_image_url: Optional[str] = Field(None, title="배경 이미지")


class LoginResponse(BaseModel):
    """로그인 응답"""
    user: UserResponse
    profile: ProfileResponse
    tokens: TokenResponse


class DeviceResponse(BaseModel):
    """기기 응답"""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., title="기기 ID")
    device_type: str = Field(..., title="기기 타입")
    device_name: Optional[str] = Field(None, title="기기 이름")
    is_active: bool = Field(..., title="활성 여부")
    last_active_at: Optional[datetime] = Field(None, title="최근 활동")
    created_at: datetime = Field(..., title="등록일시")


# ─── Internal Schemas ───

class TokenPayload(BaseModel):
    """JWT 토큰 페이로드"""
    sub: str  # user uuid
    exp: Optional[datetime] = None
    jti: Optional[str] = None  # token id (blacklist용)
