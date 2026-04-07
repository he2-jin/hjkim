"""에러 코드 정의"""


class ErrorCode:
    # Auth 관련 (81xxx - 기존 서버 네이밍 규칙 준수)
    AUTH_INVALID_CREDENTIALS = ("81001", "아이디 또는 비밀번호가 올바르지 않습니다")
    AUTH_USER_NOT_FOUND = ("81002", "사용자를 찾을 수 없습니다")
    AUTH_ACCOUNT_LOCKED = ("81003", "계정이 잠겼습니다")
    AUTH_TOKEN_EXPIRED = ("81004", "토큰이 만료되었습니다")
    AUTH_TOKEN_INVALID = ("81005", "유효하지 않은 토큰입니다")
    AUTH_SESSION_INVALID = ("81006", "유효하지 않은 세션입니다")
    AUTH_DUPLICATE_KAKAO_ID = ("81007", "이미 사용 중인 카카오톡 ID입니다")
    AUTH_DUPLICATE_PHONE = ("81008", "이미 등록된 전화번호입니다")
    AUTH_DUPLICATE_EMAIL = ("81009", "이미 등록된 이메일입니다")
    AUTH_REFRESH_TOKEN_INVALID = ("81010", "유효하지 않은 Refresh Token입니다")
    AUTH_REFRESH_TOKEN_EXPIRED = ("81011", "Refresh Token이 만료되었습니다")
    AUTH_PASSWORD_MISMATCH = ("81012", "현재 비밀번호가 올바르지 않습니다")
    AUTH_ACCOUNT_WITHDRAWN = ("81013", "탈퇴한 계정입니다")

    # Common (90xxx)
    COMMON_NOT_FOUND = ("90001", "요청한 리소스를 찾을 수 없습니다")
    COMMON_FORBIDDEN = ("90002", "접근 권한이 없습니다")
    COMMON_BAD_REQUEST = ("90003", "잘못된 요청입니다")
    COMMON_INTERNAL_ERROR = ("90004", "서버 내부 오류가 발생했습니다")
