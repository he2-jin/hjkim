import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.db.database import engine, Base
from src.routes import setup_api_routes
from src.setting import APP_NAME, APP_VERSION, ORIGINS

logger = logging.getLogger(__name__)


def get_application() -> FastAPI:
    """FastAPI 앱 생성 (기존 서버 app.py 패턴 준수)"""
    application = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS 미들웨어
    application.add_middleware(
        CORSMiddleware,
        allow_origins=ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.on_event("startup")
    async def handle_startup() -> None:
        # 테이블 생성 (개발용, 운영에서는 Alembic 사용)
        Base.metadata.create_all(bind=engine)
        # API 라우터 등록
        setup_api_routes(application)
        logger.info(f"{APP_NAME} v{APP_VERSION} started")

    @application.on_event("shutdown")
    async def handle_shutdown() -> None:
        logger.info(f"{APP_NAME} shutdown")

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc: Exception):
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {"code": "90003", "msg": str(exc)},
            },
        )

    return application


app = get_application()
