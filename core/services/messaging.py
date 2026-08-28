from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.auth.models import User
from ..models import Conversation, ConversationParticipant, Message, Post, Notification
from ..utils.media import validate_media_file

def get_or_create_direct_conversation(user1, user2):
    """
    Finds or creates a direct (1-on-1) conversation between two users.
    If the conversation was previously hidden by user1, restores visibility.
    """
    if user1 == user2:
        raise ValidationError("Cannot start a direct conversation with yourself.")

    # Find common direct conversation between user1 and user2
    user1_conv_ids = ConversationParticipant.objects.filter(
        user=user1, conversation__conversation_type=Conversation.DIRECT
    ).values_list('conversation_id', flat=True)

    shared_participant = ConversationParticipant.objects.filter(
        conversation_id__in=user1_conv_ids, user=user2
    ).first()

    if shared_participant:
        conversation = shared_participant.conversation
        # Unhide for user1 if hidden
        ConversationParticipant.objects.filter(conversation=conversation, user=user1).update(hidden_at=None)
        return conversation, False

    with transaction.atomic():
        conversation = Conversation.objects.create(
            conversation_type=Conversation.DIRECT
        )
        ConversationParticipant.objects.create(conversation=conversation, user=user1)
        ConversationParticipant.objects.create(conversation=conversation, user=user2)
        return conversation, True


def send_message(sender, conversation_id, content='', image=None, post_id=None, reply_to_id=None):
    """
    Sends a message in a conversation wrapped inside an atomic transaction.
    Validates permissions, media, shared post, and reply message.
    """
    content = (content or '').strip()
    if not content and not image and not post_id:
        raise ValidationError("Message must contain text, an image, or a shared post.")

    try:
        conversation = Conversation.objects.get(id=conversation_id)
    except Conversation.DoesNotExist:
        raise ValidationError("Conversation does not exist.")

    # Validate sender is a participant
    participant = conversation.participants.filter(user=sender).first()
    if not participant:
        raise PermissionDenied("You are not a participant in this conversation.")

    # Validate image
    if image:
        validate_media_file(image, media_types=('image',), max_size_mb=15)
        from ..utils.media import compress_and_optimize_image
        image = compress_and_optimize_image(image, max_dimension=1600, quality=85)

    # Validate shared post
    shared_post = None
    if post_id:
        try:
            shared_post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            raise ValidationError("Referenced post does not exist.")

    # Validate reply target
    parent_message = None
    if reply_to_id:
        try:
            parent_message = conversation.messages.get(id=reply_to_id, is_deleted=False)
        except Message.DoesNotExist:
            pass

    with transaction.atomic():
        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            content=content,
            image=image,
            post=shared_post,
            parent_message=parent_message
        )

        # Update sender read status & conversation touch
        now = timezone.now()
        participant.last_read_at = now
        participant.hidden_at = None
        participant.save(update_fields=['last_read_at', 'hidden_at'])

        conversation.updated_at = now
        conversation.save(update_fields=['updated_at'])

        # Unhide conversation for all other participants and create notifications
        other_participants = conversation.participants.exclude(user=sender)
        for other in other_participants:
            if other.hidden_at:
                other.hidden_at = None
                other.save(update_fields=['hidden_at'])

        return message


def get_conversation_messages(conversation, user, before_id=None, since_id=None, limit=30):
    """
    Fetches messages for a conversation with cursor pagination or incremental polling.
    - since_id: Returns only messages with id > since_id in chronological order (polling).
    - before_id: Returns messages with id < before_id for older history infinite scroll.
    - default: Returns latest limit messages in chronological order.
    """
    # Verify user participation without extra query if already cached
    has_access = False
    if hasattr(conversation, 'current_user_participant') and conversation.current_user_participant:
        has_access = True
    elif hasattr(conversation, '_prefetched_objects_cache') and 'participants' in conversation._prefetched_objects_cache:
        has_access = any(p.user_id == getattr(user, 'id', None) for p in conversation.participants.all())
    else:
        has_access = conversation.participants.filter(user=user).exists()

    if not has_access:
        raise PermissionDenied("You do not have access to this conversation.")

    qs = conversation.messages.filter(is_deleted=False).select_related(
        'sender', 'sender__profile', 'post', 'post__user', 'post__user__profile', 'parent_message', 'parent_message__sender'
    ).prefetch_related('reactions', 'reactions__user')

    if since_id:
        try:
            since_id = int(since_id)
            return list(qs.filter(id__gt=since_id).order_by('created_at'))
        except (ValueError, TypeError):
            pass

    if before_id:
        try:
            before_id = int(before_id)
            messages = list(qs.filter(id__lt=before_id).order_by('-created_at')[:limit])
            messages.reverse()
            return messages
        except (ValueError, TypeError):
            pass

    # Default latest page
    messages = list(qs.order_by('-created_at')[:limit])
    messages.reverse()
    return messages


def mark_conversation_read(conversation, user):
    """
    Marks all received unread messages as read for user in this conversation.
    """
    participant = getattr(conversation, 'current_user_participant', None)
    if not participant:
        participant = conversation.participants.filter(user=user).first()
    if not participant:
        return 0

    now = timezone.now()
    participant.last_read_at = now
    participant.save(update_fields=['last_read_at'])

    # Update unread messages sent by others
    updated = conversation.messages.filter(
        read_at__isnull=True, is_deleted=False
    ).exclude(sender=user).update(read_at=now)

    return updated


def hide_conversation(conversation, user):
    """
    Soft-hides conversation for current user without deleting message history.
    """
    participant = conversation.participants.filter(user=user).first()
    if participant:
        participant.hidden_at = timezone.now()
        participant.save(update_fields=['hidden_at'])
        return True
    return False


def unsend_message(message_id, user):
    """
    Soft-deletes a message created by the requester at any time.
    """
    try:
        message = Message.objects.get(id=message_id, sender=user)
        message.is_deleted = True
        message.save(update_fields=['is_deleted'])
        return True
    except Message.DoesNotExist:
        raise PermissionDenied("You can only delete your own messages.")


def edit_message(message_id, user, new_content):
    """
    Edits message text content strictly within 5 minutes of sending.
    """
    from datetime import timedelta
    try:
        message = Message.objects.get(id=message_id, sender=user, is_deleted=False)
    except Message.DoesNotExist:
        raise PermissionDenied("You can only edit your own messages.")

    if timezone.now() - message.created_at > timedelta(minutes=5):
        raise ValidationError("Messages can only be edited within 5 minutes of sending.")

    new_content = new_content.strip()
    if not new_content and not message.image and not message.post_id:
        raise ValidationError("Message content cannot be empty.")

    message.content = new_content
    message.is_edited = True
    message.edited_at = timezone.now()
    message.save(update_fields=['content', 'is_edited', 'edited_at'])
    return message


def toggle_reaction(message_id, user, emoji):
    """
    Toggles or updates an emoji reaction on a message.
    """
    try:
        message = Message.objects.get(id=message_id, is_deleted=False)
    except Message.DoesNotExist:
        raise ValidationError("Message does not exist.")

    if not message.conversation.participants.filter(user=user).exists():
        raise PermissionDenied("You cannot react to messages in this conversation.")

    emoji = emoji.strip()
    if not emoji:
        raise ValidationError("Emoji required.")

    from ..models import MessageReaction
    reaction, created = MessageReaction.objects.get_or_create(
        message=message, user=user, defaults={'emoji': emoji}
    )
    if not created:
        if reaction.emoji == emoji:
            reaction.delete()
        else:
            reaction.emoji = emoji
            reaction.save(update_fields=['emoji'])

    return message


def get_user_conversations(user):
    """
    Retrieves all visible conversations for a user, sorted by updated_at descending.
    Batches participants, last messages, and unread counts in memory to eliminate N+1 queries.
    """
    from collections import defaultdict

    participations = list(ConversationParticipant.objects.filter(
        user=user, hidden_at__isnull=True
    ).select_related('conversation').order_by('-conversation__updated_at'))

    conv_ids = [p.conversation_id for p in participations]
    if not conv_ids:
        return []

    # 1. Fetch all participants for these conversations
    all_participants = list(ConversationParticipant.objects.filter(
        conversation_id__in=conv_ids
    ).select_related('user', 'user__profile'))

    participants_by_conv = defaultdict(list)
    user_part_by_conv = {}
    for p in all_participants:
        participants_by_conv[p.conversation_id].append(p)
        if p.user_id == user.id:
            user_part_by_conv[p.conversation_id] = p

    # 2. Fetch recent messages to resolve last message and unread count
    from ..models import Message
    recent_messages = list(Message.objects.filter(
        conversation_id__in=conv_ids, is_deleted=False
    ).select_related('sender', 'sender__profile').order_by('conversation_id', '-created_at'))

    last_msg_by_conv = {}
    unread_counts = defaultdict(int)
    for m in recent_messages:
        if m.conversation_id not in last_msg_by_conv:
            last_msg_by_conv[m.conversation_id] = m
        user_p = user_part_by_conv.get(m.conversation_id)
        if user_p and m.sender_id != user.id:
            if not user_p.last_read_at or m.created_at > user_p.last_read_at:
                unread_counts[m.conversation_id] += 1

    # 3. Assemble pre-populated conversations
    conversations = []
    conv_dict = {p.conversation_id: p.conversation for p in participations}
    for p in participations:
        conv = conv_dict.get(p.conversation_id)
        if not conv:
            continue
        other_parts = [part for part in participants_by_conv[conv.id] if part.user_id != user.id]
        conv.partner = other_parts[0].user if other_parts else user
        conv.current_user_participant = p
        conv.cached_last_message = last_msg_by_conv.get(conv.id)
        conv.unread_count = unread_counts[conv.id]
        conversations.append(conv)

    return conversations
