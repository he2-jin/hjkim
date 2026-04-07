import uvicorn

from src.setting import HOST_NAME, PORT, DEBUG


def run():
    uvicorn.run(
        "src.app:app",
        host=HOST_NAME,
        port=PORT,
        reload=DEBUG,
        log_level="debug" if DEBUG else "info",
    )


if __name__ == "__main__":
    run()
