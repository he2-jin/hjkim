import hashlib
import uuid
from datetime import datetime, timedelta

from bcrypt import hashpw, gensalt, checkpw
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.deps import create_access_token, create_refresh_token, decode_token
from src.core.redis import redis_client
from src.errors import ErrorCode
from src.models.auth.enums import DeviceType, UserStatus
from src.models.auth.models import User, Profile, Device, RefreshToken
from src.setting import REFRESH_TOKEN_EXPIRE_DAYS, ACCESS_TOKEN_EXPIRE_MINUTES


class AuthService:
    """인증 서비스 (기존 서버 Service 패턴: @staticmethod 사용)"""

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashpw(password.encode("utf-8"), gensalt()).decode("utf-8")

    @staticmethod
    def _verify_password(plain: str, hashed: str) -> bool:
        return checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

    @staticmethod
    def _hash_phone(phone: str) -> str:
        """전화번호 SHA-256 해시 (연락처 매칭용)"""
        normalized = phone.replace("-", "").replace(" ", "")
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_token(token: str) -> str:
        """토큰 SHA-256 해시 (DB 저장용)"""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @classmethod
    def register(cls, db: Session, data: dict) -> dict:
        """
        회원가입
        - 중복 검사 (kakao_id, phone, email)
        - User + Profile + Device 생성
        - Access + Refresh Token 발급
        """
        # 중복 검사
        existing = db.execute(
            select(User).where(User.kakao_id == data["kakao_id"])
        ).scalar_one_or_none()
        if existing:
            return {"error": ErrorCode.AUTH_DUPLICATE_KAKAO_ID}

        existing = db.execute(
            select(User).where(User.phone == data["phone"])
        ).scalar_one_or_none()
        if existing:
            return {"error": ErrorCode.AUTH_DUPLICATE_PHONE}

        if data.get("email"):
            existing = db.execute(
                select(User).where(User.email == data["email"])
            ).scalar_one_or_none()
            if existing:
                return {"error": ErrorCode.AUTH_DUPLICATE_EMAIL}

        # User 생성
        user = User(
            uuid=str(uuid.uuid4()),
            kakao_id=data["kakao_id"],
            phone=data["phone"],
            phone_hash=cls._hash_phone(data["phone"]),
            email=data.get("email"),
            password_hash=cls._hash_password(data["password"]),
            name=data["name"],
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.flush()  # user.id 확보

        # Profile 생성
        profile = Profile(
            user_id=user.id,
            nickname=data["nickname"],
        )
        db.add(profile)

        # Device 생성
        device = Device(
            user_id=user.id,
            device_type=data.get("device_type", DeviceType.WEB),
            device_name=data.get("device_name"),
        )
        db.add(device)
        db.flush()

        # Token 생성
        access_token = create_access_token(user.uuid)
        refresh_token = create_refresh_token(user.uuid)

        # RefreshToken DB 저장
        rt = RefreshToken(
            user_id=user.id,
            device_id=device.id,
            token_hash=cls._hash_token(refresh_token),
            expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(rt)

        # RefreshToken Redis 저장
        redis_client.setex(
            f"refresh_token:{user.id}:{device.id}",
            timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            cls._hash_token(refresh_token),
        )

        db.commit()
        db.refresh(user)
        db.refresh(profile)

        return {
            "user": user,
            "profile": profile,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    @classmethod
    def login(cls, db: Session, kakao_id: str, password: str, device_type: str = "web", device_name: str = None) -> dict:
        """
        로그인
        - 인증 → Token 발급 → Device 등록/갱신 → last_login_at 갱신
        """
        stmt = select(User).where(User.kakao_id == kakao_id, User.deleted_at.is_(None))
        user = db.execute(stmt).scalar_one_or_none()

        if user is None:
            return {"error": ErrorCode.AUTH_INVALID_CREDENTIALS}

        if user.status == UserStatus.WITHDRAWN:
            return {"error": ErrorCode.AUTH_ACCOUNT_WITHDRAWN}

        if not cls._verify_password(password, user.password_hash):
            return {"error": ErrorCode.AUTH_INVALID_CREDENTIALS}

        # Device 조회/생성
        device = db.execute(
            select(Device).where(
                Device.user_id == user.id,
                Device.device_type == device_type,
                Device.is_active == True,
            )
        ).scalar_one_or_none()

        if device is None:
            device = Device(
                user_id=user.id,
                device_type=device_type,
                device_name=device_name,
            )
            db.add(device)
            db.flush()
        else:
            device.last_active_at = datetime.utcnow()
            if device_name:
                device.device_name = device_name

        # Token 생성
        access_token = create_access_token(user.uuid)
        refresh_token = create_refresh_token(user.uuid)

        # 기존 RefreshToken 제거 후 새로 생성
        db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.device_id == device.id,
            )
        )
        # 기존 토큰 삭제
        from sqlalchemy import delete
        db.execute(
            delete(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.device_id == device.id,
            )
        )

        rt = RefreshToken(
            user_id=user.id,
            device_id=device.id,
            token_hash=cls._hash_token(refresh_token),
            expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(rt)

        # Redis에 RefreshToken 저장
        redis_client.setex(
            f"refresh_token:{user.id}:{device.id}",
            timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            cls._hash_token(refresh_token),
        )

        # last_login_at 갱신
        user.last_login_at = datetime.utcnow()

        db.commit()

        # Profile 조회
        profile = db.execute(
            select(Profile).where(Profile.user_id == user.id)
        ).scalar_one_or_none()

        return {
            "user": user,
            "profile": profile,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    @classmethod
    def logout(cls, db: Session, user: User, access_token: str) -> dict:
        """
        로그아웃
        - Access Token blacklist 등록 (Redis)
        - Refresh Token 무효화
        """
        # Access Token blacklist
        payload = decode_token(access_token)
        if payload and payload.jti:
            remaining = ACCESS_TOKEN_EXPIRE_MINUTES * 60
            redis_client.setex(f"blacklist:{payload.jti}", remaining, "1")

        # 해당 사용자의 모든 RefreshToken Redis 키 삭제
        for key in redis_client.scan_iter(f"refresh_token:{user.id}:*"):
            redis_client.delete(key)

        # DB RefreshToken 삭제
        from sqlalchemy import delete
        db.execute(
            delete(RefreshToken).where(RefreshToken.user_id == user.id)
        )
        db.commit()

        return {"logged_out": True}

    @classmethod
    def refresh_token(cls, db: Session, refresh_token_str: str) -> dict:
        """
        Token 갱신
        - Refresh Token 검증 → 새 Access + Refresh Token 발급
        """
        payload = decode_token(refresh_token_str)
        if payload is None:
            return {"error": ErrorCode.AUTH_REFRESH_TOKEN_INVALID}

        # User 조회
        stmt = select(User).where(User.uuid == payload.sub, User.deleted_at.is_(None))
        user = db.execute(stmt).scalar_one_or_none()
        if user is None:
            return {"error": ErrorCode.AUTH_USER_NOT_FOUND}

        # DB에서 RefreshToken 검증
        token_hash = cls._hash_token(refresh_token_str)
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.token_hash == token_hash,
        )
        rt = db.execute(stmt).scalar_one_or_none()
        if rt is None:
            return {"error": ErrorCode.AUTH_REFRESH_TOKEN_INVALID}

        if rt.expires_at < datetime.utcnow():
            return {"error": ErrorCode.AUTH_REFRESH_TOKEN_EXPIRED}

        # 새 토큰 발급
        new_access_token = create_access_token(user.uuid)
        new_refresh_token = create_refresh_token(user.uuid)

        # 기존 RT 갱신
        rt.token_hash = cls._hash_token(new_refresh_token)
        rt.expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        # Redis 갱신
        redis_client.setex(
            f"refresh_token:{user.id}:{rt.device_id}",
            timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            cls._hash_token(new_refresh_token),
        )

        db.commit()

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
        }

    @classmethod
    def change_password(cls, db: Session, user: User, current_password: str, new_password: str) -> dict:
        """비밀번호 변경"""
        if not cls._verify_password(current_password, user.password_hash):
            return {"error": ErrorCode.AUTH_PASSWORD_MISMATCH}

        user.password_hash = cls._hash_password(new_password)
        db.commit()

        return {"changed": True}

    @staticmethod
    def get_devices(db: Session, user: User) -> list:
        """로그인된 디바이스 목록"""
        stmt = select(Device).where(Device.user_id == user.id, Device.is_active == True)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def deactivate_device(db: Session, user: User, device_id: int) -> dict:
        """특정 디바이스 로그아웃"""
        stmt = select(Device).where(
            Device.id == device_id,
            Device.user_id == user.id,
        )
        device = db.execute(stmt).scalar_one_or_none()
        if device is None:
            return {"error": ErrorCode.COMMON_NOT_FOUND}

        device.is_active = False

        # 해당 디바이스의 RefreshToken 삭제
        from sqlalchemy import delete
        db.execute(
            delete(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.device_id == device_id,
            )
        )
        redis_client.delete(f"refresh_token:{user.id}:{device_id}")

        db.commit()

        return {"deactivated": True}
