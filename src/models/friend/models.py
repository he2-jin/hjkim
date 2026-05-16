from datetime import datetime

from sqlalchemy import (
    BigInteger, String, DateTime, Boolean, Enum,
    ForeignKey, UniqueConstraint, Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base
from src.models.friend.enums import FriendStatus


class Friend(Base):
    """친구 관계 테이블 — 단방향 관계 (A가 B를 추가해도 B 입장에서는 별도 row)"""
    __tablename__ = "friends"

    # Mapped[int] = "파이썬에서 이 컬럼은 정수"
    # mapped_column(BigInteger, ...) = "DB에서는 BIGINT 타입의 기본키"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # nullable=False → 이 컬럼은 반드시 값이 있어야 함
    # ondelete="CASCADE" → users 테이블의 row가 삭제되면 이 row도 자동 삭제
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # friend_user_id: 친구로 추가된 상대방의 user.id
    friend_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Mapped[str] = 문자열 (nullable=False이므로 None 불가)
    # default=FriendStatus.NORMAL → 추가 시 기본값은 '일반' 상태
    status: Mapped[str] = mapped_column(
        Enum(FriendStatus), nullable=False, default=FriendStatus.NORMAL
    )

    # Mapped[bool] = True/False 값
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Mapped[str | None] = 문자열 또는 None (nullable 컬럼)
    # 별명은 선택값이므로 None 허용
    custom_name: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    # onupdate=datetime.utcnow → DB row가 수정될 때마다 자동으로 현재 시각으로 갱신
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships — user_id, friend_user_id 둘 다 User.id를 가리키므로
    # foreign_keys= 로 각각 어떤 FK를 쓸지 명시해야 SQLAlchemy가 혼동하지 않음
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    friend_user: Mapped["User"] = relationship("User", foreign_keys=[friend_user_id])

    __table_args__ = (
        # (user_id, friend_user_id) 조합은 DB 레벨에서 중복 저장 불가
        # → 같은 친구를 두 번 추가하면 DB 자체가 에러를 낸다
        UniqueConstraint("user_id", "friend_user_id", name="uq_friend_pair"),
        # 친구 목록 조회 시 (user_id + status) 조합으로 자주 검색하므로 인덱스 생성
        # → 인덱스가 없으면 전체 테이블을 스캔해서 느려짐
        Index("idx_friend_user_status", "user_id", "status"),
    )
