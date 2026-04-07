from fastapi import HTTPException, status


def bad_credentials(msg: str = "Not Authenticated") -> HTTPException:
    """인증 실패 예외"""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=msg,
        headers={"WWW-Authenticate": "Bearer"},
    )


def raise_forbidden(msg: str = "Forbidden") -> HTTPException:
    """권한 없음 예외"""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=msg,
    )


def raise_not_found(msg: str = "Not Found") -> HTTPException:
    """리소스 없음 예외"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=msg,
    )


def raise_bad_request(msg: str = "Bad Request") -> HTTPException:
    """잘못된 요청 예외"""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=msg,
    )


def raise_conflict(msg: str = "Conflict") -> HTTPException:
    """충돌 예외 (중복 등)"""
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=msg,
    )
