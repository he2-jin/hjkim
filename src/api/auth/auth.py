from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.api.deps import get_db, get_current_user, oauth2_scheme
from src.models.auth.models import User
from src.models.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenRefreshRequest,
    PasswordChangeRequest,
    LoginResponse,
    UserResponse,
    ProfileResponse,
    TokenResponse,
    DeviceResponse,
)
from src.models.base import api_res
from src.services.auth.auth import AuthService

router = APIRouter(default_response_class=JSONResponse)


@router.post("/register")
def register(
    body: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """회원가입"""
    result = AuthService.register(db, body.model_dump())

    if "error" in result:
        code, msg = result["error"]
        return api_res(success=False, error_code=code, error_msg=msg)

    user = result["user"]
    profile = result["profile"]

    # 쿠키에 토큰 설정 (기존 서버 패턴)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {result['access_token']}",
        httponly=True,
        samesite="lax",
    )

    return api_res(
        success=True,
        data={
            "user": UserResponse.model_validate(user).model_dump(),
            "profile": ProfileResponse.model_validate(profile).model_dump(),
            "tokens": {
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "token_type": "bearer",
            },
        },
    )


@router.post("/login")
def login(
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """로그인"""
    result = AuthService.login(
        db,
        kakao_id=body.kakao_id,
        password=body.password,
        device_type=body.device_type,
        device_name=body.device_name,
    )

    if "error" in result:
        code, msg = result["error"]
        return api_res(success=False, error_code=code, error_msg=msg)

    user = result["user"]
    profile = result["profile"]

    response.set_cookie(
        key="access_token",
        value=f"Bearer {result['access_token']}",
        httponly=True,
        samesite="lax",
    )

    return api_res(
        success=True,
        data={
            "user": UserResponse.model_validate(user).model_dump(),
            "profile": ProfileResponse.model_validate(profile).model_dump() if profile else {},
            "tokens": {
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "token_type": "bearer",
            },
        },
    )


@router.post("/logout")
def logout(
    response: Response,
    token: str = Depends(oauth2_scheme),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """로그아웃"""
    AuthService.logout(db, user, token)

    response.delete_cookie(key="access_token")

    return api_res(success=True, data={"message": "로그아웃 되었습니다"})


@router.post("/token/refresh")
def refresh_token(
    body: TokenRefreshRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """Access Token 갱신"""
    result = AuthService.refresh_token(db, body.refresh_token)

    if "error" in result:
        code, msg = result["error"]
        return api_res(success=False, error_code=code, error_msg=msg)

    response.set_cookie(
        key="access_token",
        value=f"Bearer {result['access_token']}",
        httponly=True,
        samesite="lax",
    )

    return api_res(
        success=True,
        data={
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "token_type": "bearer",
        },
    )


@router.post("/password/change")
def change_password(
    body: PasswordChangeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """비밀번호 변경"""
    result = AuthService.change_password(
        db, user, body.current_password, body.new_password
    )

    if "error" in result:
        code, msg = result["error"]
        return api_res(success=False, error_code=code, error_msg=msg)

    return api_res(success=True, data={"message": "비밀번호가 변경되었습니다"})


@router.get("/devices")
def get_devices(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """로그인된 디바이스 목록"""
    devices = AuthService.get_devices(db, user)
    return api_res(
        success=True,
        data=[DeviceResponse.model_validate(d).model_dump() for d in devices],
    )


@router.delete("/devices/{device_id}")
def deactivate_device(
    device_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """특정 디바이스 로그아웃"""
    result = AuthService.deactivate_device(db, user, device_id)

    if "error" in result:
        code, msg = result["error"]
        return api_res(success=False, error_code=code, error_msg=msg)

    return api_res(success=True, data={"message": "디바이스가 로그아웃 되었습니다"})
