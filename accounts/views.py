from django.http import JsonResponse
from django.core.cache import cache
from redis import Redis
import os


def check_redis(request):
    cache_status = False
    redis_status = False

    # Kiểm tra Django cache (sử dụng Redis)
    try:
        cache.set("test_cache", "working", 10)
        if cache.get("test_cache") == "working":
            cache_status = True
    except Exception as e:
        cache_error = str(e)

    # Kiểm tra kết nối Redis trực tiếp
    try:
        r = Redis(
            host=os.environ.get("REDIS_HOST", "redis"),
            port=int(os.environ.get("REDIS_PORT", 6379)),
        )
        if r.ping():
            redis_status = True
    except Exception as e:
        redis_error = str(e)

    return JsonResponse({"cache_status": cache_status, "redis_status": redis_status})
