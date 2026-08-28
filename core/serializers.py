from django.utils import timezone
from .utils.media import get_media_url

def serialize_user(user):
    """Serializes basic user info with real-time online status."""
    if not user:
        return None
    profile = getattr(user, 'profile', None)
    avatar_url = get_media_url(profile.profile_pic) if profile else None
    is_online = profile.is_online if profile else False
    online_status_text = profile.online_status_text if profile else "Offline"
    return {
        'id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'profile_pic': avatar_url,
        'is_online': is_online,
        'online_status_text': online_status_text,
    }

def serialize_post_preview(post):
    """Serializes a lightweight preview of a shared post for DMs."""
    if not post:
        return None
    return {
        'id': post.id,
        'username': post.user.username,
        'user_avatar': get_media_url(post.user.profile.profile_pic) if hasattr(post.user, 'profile') else None,
        'caption': post.caption[:120] if post.caption else '',
        'image_url': post.get_image_url,
        'video_url': post.get_video_url,
    }

def serialize_message(message, current_user=None):
    """Serializes a Message model instance into a rich DTO dictionary."""
    if not message:
        return None

    is_mine = (message.sender == current_user) if current_user else False
    sender_avatar = get_media_url(message.sender.profile.profile_pic) if hasattr(message.sender, 'profile') else None

    # Reply preview
    reply_preview = None
    if message.parent_message and not message.parent_message.is_deleted:
        reply_preview = {
            'id': message.parent_message.id,
            'sender_username': message.parent_message.sender.username,
            'content': message.parent_message.content[:80] if message.parent_message.content else ('[Image]' if message.parent_message.image else '[Post]'),
        }

    formatted_time = message.created_at.strftime('%I:%M %p').lstrip('0')
    formatted_date = message.created_at.strftime('%b %d, %Y')

    reactions = []
    if hasattr(message, '_prefetched_objects_cache') and 'reactions' in message._prefetched_objects_cache:
        reaction_objs = message.reactions.all()
    else:
        reaction_objs = message.reactions.select_related('user').all()

    for r in reaction_objs:
        reactions.append({
            'user_id': r.user_id,
            'username': r.user.username,
            'emoji': r.emoji,
            'is_mine': (r.user_id == getattr(current_user, 'id', None)) if current_user else False,
        })

    return {
        'id': message.id,
        'conversation_id': message.conversation_id,
        'sender': serialize_user(message.sender),
        'sender_id': message.sender_id,
        'sender_username': message.sender.username,
        'sender_avatar': sender_avatar,
        'content': message.content,
        'image_url': message.get_image_url,
        'shared_post': serialize_post_preview(message.post),
        'reply_to': reply_preview,
        'read_at': message.read_at.strftime('%I:%M %p').lstrip('0') if message.read_at else None,
        'is_read': bool(message.read_at),
        'is_mine': is_mine,
        'is_edited': message.is_edited,
        'can_edit': message.can_edit(current_user),
        'can_delete': message.can_delete(current_user),
        'reactions': reactions,
        'created_at_iso': message.created_at.isoformat(),
        'created_at_time': formatted_time,
        'created_at_date': formatted_date,
    }

def serialize_conversation(conversation, current_user):
    """Serializes a Conversation model instance for the inbox conversation drawer."""
    if not conversation:
        return None

    partner = conversation.get_partner(current_user)
    last_message = conversation.get_last_message()
    unread_count = conversation.get_unread_count(current_user)

    last_msg_data = None
    if last_message:
        last_msg_data = {
            'id': last_message.id,
            'sender_username': last_message.sender.username,
            'is_mine': last_message.sender == current_user,
            'content': last_message.content if last_message.content else ('📷 Photo' if last_message.image else '📎 Post'),
            'created_at_time': last_message.created_at.strftime('%I:%M %p').lstrip('0'),
            'created_at_iso': last_message.created_at.isoformat(),
        }

    return {
        'id': conversation.id,
        'type': conversation.conversation_type,
        'title': conversation.title if conversation.title else (partner.username if partner else 'Direct'),
        'partner': serialize_user(partner) if partner else None,
        'last_message': last_msg_data,
        'unread_count': unread_count,
        'updated_at_iso': conversation.updated_at.isoformat(),
    }
