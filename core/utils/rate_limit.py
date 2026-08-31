from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from django.contrib import messages
from django.shortcuts import redirect

def get_client_ip(request):
    """Extracts client IP from proxy headers or remote address."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')

def rate_limit(key_prefix='rl', limit=20, period=60, is_json=False):
    """
    Sliding window cache-backed rate limiter.
    - key_prefix: Unique identifier for the action (e.g. 'login', 'dm_send')
    - limit: Maximum requests allowed within period
    - period: Window in seconds
    - is_json: When True or for XMLHttpRequest, returns HTTP 429 JSON
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Only throttle state-mutating requests (POST, PUT, DELETE)
            if request.method in ('POST', 'PUT', 'DELETE'):
                ip = get_client_ip(request)
                user_id = request.user.id if request.user.is_authenticated else 'anon'
                cache_key = f"rl:{key_prefix}:{user_id}:{ip}"

                try:
                    count = cache.get(cache_key, 0)
                    if count >= limit:
                        if is_json or request.headers.get('x-requested-with') == 'XMLHttpRequest':
                            return JsonResponse({
                                'success': False,
                                'error': 'Too many requests. Please wait a moment and try again.'
                            }, status=429)
                        referer = request.META.get('HTTP_REFERER')
                        messages.error(request, 'Too many requests. Please wait a moment and try again.')
                        return redirect(referer if referer else 'home')

                    if count == 0:
                        cache.set(cache_key, 1, timeout=period)
                    else:
                        cache.incr(cache_key)
                except Exception:
                    # Fail open if cache is temporarily unavailable
                    pass

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
