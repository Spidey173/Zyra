import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.http import require_POST, require_GET
from django.core.exceptions import ValidationError, PermissionDenied
from django.db.models import Q
from ..models import Conversation, ConversationParticipant, Message, Post
from ..services.messaging import (
    get_or_create_direct_conversation,
    send_message,
    get_conversation_messages,
    mark_conversation_read,
    hide_conversation,
    unsend_message,
    edit_message,
    toggle_reaction,
    get_user_conversations,
)
from ..serializers import (
    serialize_user,
    serialize_message,
    serialize_conversation,
    serialize_post_preview
)

@login_required
def direct_inbox(request, username=None):
    """
    Main Instagram Direct inbox interface.
    - If username is provided, opens/creates direct conversation with that user.
    - Renders dual-column view: Conversations on left, active chat on right.
    """
    conversations = get_user_conversations(request.user)
    for c in conversations:
        c.partner = c.get_partner(request.user)
        c.unread_count = c.get_unread_count(request.user)
    active_conversation = None
    initial_partner = None

    if username:
        if username == request.user.username:
            # Cannot direct message yourself
            return redirect('direct_inbox')
        target_user = get_object_or_404(User, username=username)
        try:
            active_conversation, _ = get_or_create_direct_conversation(request.user, target_user)
            initial_partner = target_user
        except ValidationError:
            return redirect('direct_inbox')
    elif conversations:
        # Default to first conversation if available
        active_conversation = conversations[0]
        initial_partner = active_conversation.get_partner(request.user)

    initial_messages = []
    if active_conversation:
        try:
            raw_msgs = get_conversation_messages(active_conversation, request.user, limit=40)
            initial_messages = [serialize_message(m, request.user) for m in raw_msgs]
            mark_conversation_read(active_conversation, request.user)
        except PermissionDenied:
            active_conversation = None

    # Serialized conversations list for instant frontend hydration
    conversations_data = [serialize_conversation(c, request.user) for c in conversations]

    context = {
        'conversations': conversations,
        'conversations_data': conversations_data,
        'conversations_json': json.dumps(conversations_data),
        'active_conversation': active_conversation,
        'active_partner': initial_partner,
        'initial_messages': initial_messages,
        'initial_messages_json': json.dumps(initial_messages),
    }
    return render(request, 'core/direct.html', context)


@login_required
@require_POST
def send_message_api(request, conversation_id):
    """AJAX endpoint to send a message (text, image, shared post, or reply)."""
    content = request.POST.get('content', '')
    image = request.FILES.get('image')
    post_id = request.POST.get('post_id')
    reply_to_id = request.POST.get('reply_to_id')

    try:
        msg = send_message(
            sender=request.user,
            conversation_id=conversation_id,
            content=content,
            image=image,
            post_id=post_id,
            reply_to_id=reply_to_id
        )
        return JsonResponse({
            'success': True,
            'message': serialize_message(msg, request.user)
        })
    except PermissionDenied as e:
        return HttpResponseForbidden(str(e))
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Failed to send message.'}, status=500)


@login_required
@require_GET
def get_messages_api(request, conversation_id):
    """
    Incremental polling or cursor pagination endpoint.
    - ?since_id=<id>: Returns only new messages received after since_id.
    - ?before_id=<id>&limit=30: Returns older messages for scroll-up pagination.
    """
    conversation = get_object_or_404(Conversation, id=conversation_id)
    since_id = request.GET.get('since_id')
    before_id = request.GET.get('before_id')
    limit = int(request.GET.get('limit', 30))

    try:
        messages = get_conversation_messages(
            conversation=conversation,
            user=request.user,
            before_id=before_id,
            since_id=since_id,
            limit=limit
        )

        if messages:
            mark_conversation_read(conversation, request.user)

        serialized = [serialize_message(m, request.user) for m in messages]
        return JsonResponse({
            'success': True,
            'messages': serialized,
            'count': len(serialized)
        })
    except PermissionDenied as e:
        return HttpResponseForbidden(str(e))


@login_required
@require_POST
def mark_as_read_api(request, conversation_id):
    """Marks conversation as read."""
    conversation = get_object_or_404(Conversation, id=conversation_id)
    updated_count = mark_conversation_read(conversation, request.user)
    return JsonResponse({'success': True, 'marked_read': updated_count})


@login_required
@require_GET
def search_users_for_dm(request):
    """Searches users by username or name to start a new direct conversation."""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'users': []})

    users = User.objects.filter(
        Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
    ).exclude(id=request.user.id).select_related('profile')[:10]

    return JsonResponse({
        'users': [serialize_user(u) for u in users]
    })


@login_required
@require_POST
def share_post_to_dm(request):
    """Shares a post into direct message with a specific user."""
    target_username = request.POST.get('username')
    post_id = request.POST.get('post_id')
    optional_note = request.POST.get('note', '')

    if not target_username or not post_id:
        return HttpResponseBadRequest("Username and post_id required.")

    target_user = get_object_or_404(User, username=target_username)
    post = get_object_or_404(Post, id=post_id)

    try:
        conv, _ = get_or_create_direct_conversation(request.user, target_user)
        msg = send_message(
            sender=request.user,
            conversation_id=conv.id,
            content=optional_note,
            post_id=post.id
        )
        return JsonResponse({
            'success': True,
            'conversation_id': conv.id,
            'message': serialize_message(msg, request.user)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def unsend_message_api(request, message_id):
    """Soft-deletes a message created by current user."""
    try:
        unsend_message(message_id, request.user)
        return JsonResponse({'success': True})
    except PermissionDenied as e:
        return HttpResponseForbidden(str(e))
    except Exception:
        return JsonResponse({'success': False, 'error': 'Message not found.'}, status=404)


@login_required
@require_POST
def hide_conversation_api(request, conversation_id):
    """Hides conversation from current user's inbox list."""
    conversation = get_object_or_404(Conversation, id=conversation_id)
    hide_conversation(conversation, request.user)
    return JsonResponse({'success': True})


@login_required
@require_POST
def edit_message_api(request, message_id):
    """Edits message content (strictly within 5 minutes of creation)."""
    new_content = request.POST.get('content', '').strip()
    if not new_content:
        return JsonResponse({'success': False, 'error': 'Message content cannot be empty.'}, status=400)

    try:
        msg = edit_message(message_id, request.user, new_content)
        return JsonResponse({
            'success': True,
            'message': serialize_message(msg, request.user)
        })
    except PermissionDenied as e:
        return HttpResponseForbidden(str(e))
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Failed to edit message.'}, status=500)


@login_required
@require_POST
def react_message_api(request, message_id):
    """Toggles or updates an emoji reaction on a message."""
    emoji = request.POST.get('emoji', '').strip()
    if not emoji:
        return JsonResponse({'success': False, 'error': 'Emoji is required.'}, status=400)

    try:
        msg = toggle_reaction(message_id, request.user, emoji)
        return JsonResponse({
            'success': True,
            'message': serialize_message(msg, request.user)
        })
    except PermissionDenied as e:
        return HttpResponseForbidden(str(e))
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Failed to react to message.'}, status=500)
