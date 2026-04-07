import redis

from src.setting import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD


def get_redis_client() -> redis.Redis:
    """Redis 클라이언트 생성"""
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD or None,
        decode_responses=True,
    )


redis_client = get_redis_client()
