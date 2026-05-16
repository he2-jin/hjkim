import enum


class FriendStatus(str, enum.Enum):
    # 일반 친구 관계 (목록에 표시됨)
    NORMAL = "normal"
    # 차단 상태 (목록에서 숨겨짐, 재추가 불가)
    BLOCKED = "blocked"
    # 숨김 상태 (목록에서 제외, 향후 확장용 — 이번 MVP에서 API는 없음)
    HIDDEN = "hidden"
