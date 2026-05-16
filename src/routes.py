from fastapi import FastAPI, APIRouter

from src.api.auth.auth import router as auth_router
from src.api.friend.friend import router as friend_router


def setup_api_routes(application: FastAPI) -> None:
    """API 라우터 등록 (기존 서버 routes.py 패턴 준수)"""
    api_router = APIRouter()

    api_router.include_router(
        auth_router,
        prefix="/auth",
        tags=["auth"],
    )

    api_router.include_router(
        friend_router,
        prefix="/friend",
        tags=["friend"],
    )

    # TODO: UC-3 구현 시 추가
    # api_router.include_router(chat_room_router, prefix="/chat", tags=["chat"])

    application.include_router(api_router, prefix="/api")
