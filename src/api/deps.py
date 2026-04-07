import uuid
from datetime import datetime, timedelta
from typing import Generator, Optional

from fastapi import Depends, Request
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security import OAuth2
from fastapi.security.utils import get_authorization_scheme_param
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.database import SessionLocal
from src.middlewares.exceptions import bad_credentials
from src.models.auth.models import User
from src.models.auth.schemas import TokenPayload
from src.setting import (
    SECRET_KEY, ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS,
)


# ─── DB Dependency ───

def get_db() -> Generator:
    """DB 세션 생성 (기존 서버 패턴 준수)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── OAuth2 with Cookie Support (기존 서버 패턴) ───

class OAuth2PasswordBearerWithCookie(OAuth2):
    def __init__(
        self,
        tokenUrl: str,
        scheme_name: str = None,
        scopes: dict = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(password={"tokenUrl": tokenUrl, "scopes": scopes})
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        header_authorization: str = request.headers.get("Authorization")
        cookie_authorization: str = request.cookies.get("access_token")

        header_scheme, header_param = get_authorization_scheme_param(header_authorization)
        cookie_scheme, cookie_param = get_authorization_scheme_param(cookie_authorization)

        if cookie_scheme.lower() == "bearer":
            param = cookie_param
        elif header_scheme.lower() == "bearer":
            param = header_param
        else:
            if self.auto_error:
                bad_credentials(msg="Not Authenticated")
            return None

        return param


oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="/api/auth/login")


# ─── Token 생성/검증 ───

def create_access_token(user_uuid: str) -> str:
    """Access Token 생성"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    jti = str(uuid.uuid4())
    to_encode = {
        "sub": user_uuid,
        "exp": expire,
        "jti": jti,
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_uuid: str) -> str:
    """Refresh Token 생성"""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    to_encode = {
        "sub": user_uuid,
        "exp": expire,
        "jti": jti,
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    """토큰 디코딩"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        bad_credentials(msg="토큰이 만료되었습니다")
    except (JWTError, Exception):
        bad_credentials(msg="유효하지 않은 토큰입니다")


# ─── Current User Dependency ───

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """현재 인증된 사용자 반환 (기존 서버 get_current_admin 패턴 준수)"""
    from src.core.redis import redis_client

    payload = decode_token(token)
    if payload is None:
        bad_credentials(msg="Not Authenticated")

    # Blacklist 확인
    if payload.jti and redis_client.get(f"blacklist:{payload.jti}"):
        bad_credentials(msg="로그아웃된 토큰입니다")

    # DB에서 사용자 조회 (SQLAlchemy 2.0 select 문법)
    stmt = select(User).where(User.uuid == payload.sub, User.deleted_at.is_(None))
    user = db.execute(stmt).scalar_one_or_none()

    if user is None:
        bad_credentials(msg="사용자를 찾을 수 없습니다")

    if user.status != "active":
        bad_credentials(msg="비활성 계정입니다")

    return user
