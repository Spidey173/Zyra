from django.conf import settings
from django.db.models import Q, F
from django.core.cache import cache
from .models import Notification, Message

def app_settings(request):
    """Global template context variables for branding and badges with short caching."""
    context = {
        'APP_NAME': getattr(settings, 'APP_NAME', 'Zyra'),
    }
    if request.user.is_authenticated:
        cache_key = f"user_badges_{request.user.id}"
        cached_badges = cache.get(cache_key)
        if cached_badges is not None:
            context.update(cached_badges)
        else:
            # Fast query for unread notifications
            try:
                unread_notifications_count = Notification.objects.filter(
                    receiver=request.user, notification_type__in=['comment', 'follow'], is_read=False
                ).count()
            except Exception:
                unread_notifications_count = 0

            # Fast single query for unread direct conversations
            try:
                unread_direct_count = Message.objects.filter(
                    conversation__participants__user=request.user,
                    conversation__participants__hidden_at__isnull=True
                ).exclude(
                    sender=request.user
                ).filter(
                    Q(conversation__participants__last_read_at__isnull=True) |
                    Q(created_at__gt=F('conversation__participants__last_read_at'))
                ).values('conversation_id').distinct().count()
            except Exception:
                unread_direct_count = 0

            badges = {
                'unread_notifications_count': unread_notifications_count,
                'unread_direct_count': unread_direct_count,
            }
            cache.set(cache_key, badges, 15)
            context.update(badges)
    else:
        context['unread_notifications_count'] = 0
        context['unread_direct_count'] = 0

    return context
