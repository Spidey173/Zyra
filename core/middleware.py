from django.utils import timezone
from datetime import timedelta

class UpdateLastSeenMiddleware:
    """
    Middleware that records user activity and updates UserProfile.last_seen
    every 60 seconds for accurate real-time online/offline presence.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            now = timezone.now()
            last_seen = request.user.profile.last_seen
            if not last_seen or (now - last_seen) > timedelta(seconds=60):
                request.user.profile.last_seen = now
                request.user.profile.save(update_fields=['last_seen'])
        return self.get_response(request)
