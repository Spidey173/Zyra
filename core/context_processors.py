from django.conf import settings
from .models import ConversationParticipant, Notification

def app_settings(request):
    """Global template context variables for branding and badges."""
    context = {
        'APP_NAME': getattr(settings, 'APP_NAME', 'Zyra'),
    }
    if request.user.is_authenticated:
        # Calculate unread notifications count (Comments and Follows only)
        try:
            context['unread_notifications_count'] = Notification.objects.filter(
                receiver=request.user, notification_type__in=['comment', 'follow'], is_read=False
            ).count()
        except Exception:
            context['unread_notifications_count'] = 0

        # Calculate unread conversations count
        try:
            # Check for any participant entry where conversation has messages after last_read_at
            from .models import Conversation
            unread_chats = 0
            participants = ConversationParticipant.objects.filter(
                user=request.user, hidden_at__isnull=True
            ).select_related('conversation')
            for p in participants:
                last_msg = p.conversation.messages.exclude(sender=request.user).order_by('-created_at').first()
                if last_msg:
                    if not p.last_read_at or last_msg.created_at > p.last_read_at:
                        unread_chats += 1
            context['unread_direct_count'] = unread_chats
        except Exception:
            context['unread_direct_count'] = 0
    else:
        context['unread_notifications_count'] = 0
        context['unread_direct_count'] = 0

    return context
