from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from src.errors import ErrorCode
from src.models.auth.models import User, Profile
from src.models.friend.enums import FriendStatus
from src.models.friend.models import Friend


class FriendService:
    """친구 서비스 — 기존 AuthService와 동일한 @classmethod 패턴 사용"""

    @classmethod
    def get_friends(cls, db: Session, user: User) -> list:
        """NORMAL 상태 친구 목록 조회 — 즐겨찾기 우선, 추가일 오래된 순 정렬

        joinedload: Friend → User → Profile 을 한 번의 SQL JOIN으로 가져옴
        (쓰지 않으면 친구 N명 조회 시 N+1번 쿼리 발생)
        """
        stmt = (
            select(Friend)
            .where(
                Friend.user_id == user.id,
                Friend.status == FriendStatus.NORMAL,
            )
            .options(
                # Friend.friend_user(User) 를 조회할 때 User.profile 도 같이 JOIN
                joinedload(Friend.friend_user).joinedload(User.profile)
            )
            .order_by(Friend.is_favorite.desc(), Friend.created_at.asc())
        )
        # .unique() → joinedload 사용 시 중복 row가 생길 수 있어서 반드시 호출
        return list(db.execute(stmt).scalars().unique().all())

    @classmethod
    def search_by_kakao_id(cls, db: Session, kakao_id: str) -> dict:
        """카카오톡 ID로 유저 검색 — 탈퇴/삭제 계정 제외"""
        user = db.execute(
            select(User).where(
                User.kakao_id == kakao_id,
                User.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if user is None:
            return {"error": ErrorCode.FRIEND_USER_NOT_FOUND}

        profile = db.execute(
            select(Profile).where(Profile.user_id == user.id)
        ).scalar_one_or_none()

        return {"user": user, "profile": profile}

    @classmethod
    def add_friend(cls, db: Session, user: User, friend_uuid: str) -> dict:
        """친구 추가 — 자기 자신, 중복, 존재하지 않는 유저 검증 포함

        검증 순서:
        1. UUID로 대상 유저 존재 확인
        2. 자기 자신 추가 시도 차단
        3. 이미 Friend row 존재 여부 확인 (status 무관)
        4. Friend row 생성
        """
        # 1. 대상 유저 존재 확인
        target = db.execute(
            select(User).where(
                User.uuid == friend_uuid,
                User.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if target is None:
            return {"error": ErrorCode.FRIEND_USER_NOT_FOUND}

        # 2. 자기 자신 체크
        if user.id == target.id:
            return {"error": ErrorCode.FRIEND_SELF_ADD}

        # 3. 이미 Friend row가 있는지 체크 (NORMAL, BLOCKED, HIDDEN 모두 포함)
        existing = db.execute(
            select(Friend).where(
                Friend.user_id == user.id,
                Friend.friend_user_id == target.id,
            )
        ).scalar_one_or_none()

        if existing:
            return {"error": ErrorCode.FRIEND_ALREADY_EXISTS}

        # 4. Friend 생성
        friend = Friend(user_id=user.id, friend_user_id=target.id)
        db.add(friend)
        db.commit()

        # 커밋 후 joinedload로 재조회하여 friend_user + profile 포함된 상태로 반환
        friend = db.execute(
            select(Friend)
            .where(Friend.id == friend.id)
            .options(joinedload(Friend.friend_user).joinedload(User.profile))
        ).scalar_one()

        return {"friend": friend}

    @classmethod
    def sync_contacts(cls, db: Session, user: User, phone_hashes: list[str]) -> dict:
        """연락처 동기화 — phone_hash 기반 매칭, raw 전화번호 미사용

        처리 순서:
        1. phone_hashes로 User + Profile 일괄 조회 (자신 제외)
        2. 이미 Friend row가 있는 user_id 제외
        3. 나머지 매칭 유저 반환
        """
        # 1. phone_hash 일치하는 유저 + 프로필 조회 (자신 제외)
        # isouter=True → 프로필 없는 유저도 포함 (LEFT OUTER JOIN)
        rows = db.execute(
            select(User, Profile)
            .join(Profile, Profile.user_id == User.id, isouter=True)
            .where(
                User.phone_hash.in_(phone_hashes),
                User.deleted_at.is_(None),
                User.id != user.id,
            )
        ).all()

        if not rows:
            return {"matched": []}

        # 2. 이미 친구 관계인 user_id 목록 조회
        matched_ids = [row[0].id for row in rows]
        existing_friend_ids = set(
            db.execute(
                select(Friend.friend_user_id).where(
                    Friend.user_id == user.id,
                    Friend.friend_user_id.in_(matched_ids),
                )
            ).scalars().all()
        )

        # 3. 이미 친구인 유저 제외
        result = [
            (u, p) for u, p in rows
            if u.id not in existing_friend_ids
        ]

        return {"matched": result}

    @classmethod
    def toggle_favorite(cls, db: Session, user: User, friend_id: int) -> dict:
        """즐겨찾기 토글 — NORMAL 상태 친구만 허용"""
        friend = db.execute(
            select(Friend).where(
                Friend.id == friend_id,
                Friend.user_id == user.id,
                # BLOCKED/HIDDEN 상태 친구는 즐겨찾기 불가
                Friend.status == FriendStatus.NORMAL,
            )
        ).scalar_one_or_none()

        if friend is None:
            return {"error": ErrorCode.FRIEND_NOT_FOUND}

        friend.is_favorite = not friend.is_favorite
        db.commit()
        db.refresh(friend)

        return {"friend": friend}

    @classmethod
    def block_friend(cls, db: Session, user: User, friend_id: int) -> dict:
        """차단 — NORMAL 상태 친구만 BLOCKED로 전환"""
        friend = db.execute(
            select(Friend).where(
                Friend.id == friend_id,
                Friend.user_id == user.id,
                Friend.status == FriendStatus.NORMAL,
            )
        ).scalar_one_or_none()

        if friend is None:
            return {"error": ErrorCode.FRIEND_NOT_FOUND}

        friend.status = FriendStatus.BLOCKED
        db.commit()

        return {"friend": friend}

    @classmethod
    def delete_friend(cls, db: Session, user: User, friend_id: int) -> dict:
        """친구 삭제 — hard delete (row 물리적 제거), status 무관하게 삭제 허용

        hard delete를 선택한 이유:
        친구 관계는 감사 이력이 필요 없는 단순 관계 레코드이므로
        soft delete 대신 row를 완전히 제거한다.
        삭제 후 같은 상대를 재추가하면 새 row가 생성된다.
        """
        friend = db.execute(
            select(Friend).where(
                Friend.id == friend_id,
                Friend.user_id == user.id,
            )
        ).scalar_one_or_none()

        if friend is None:
            return {"error": ErrorCode.FRIEND_NOT_FOUND}

        db.delete(friend)
        db.commit()

        return {"deleted": True}
