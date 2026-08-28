from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Count
from ..models import Post, Like, Follow

@login_required
def explore_view(request):
    """Explore and search page with batched relationship queries."""
    query = request.GET.get('q', '').strip()
    users_results = []
    posts_results = []

    if query:
        users_results = list(User.objects.filter(
            Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query)
        ).exclude(id=request.user.id).select_related('profile'))

        posts_results = list(Post.objects.filter(
            Q(caption__icontains=query) | Q(user__username__icontains=query)
        ).select_related('user', 'user__profile').prefetch_related('likes', 'comments'))

        if users_results:
            u_ids = [u.id for u in users_results]
            followed_ids = set(Follow.objects.filter(follower=request.user, following_id__in=u_ids).values_list('following_id', flat=True))
            for u in users_results:
                u.is_followed_by_user = u.id in followed_ids

        if posts_results:
            p_ids = [p.id for p in posts_results]
            liked_ids = set(Like.objects.filter(user=request.user, post_id__in=p_ids).values_list('post_id', flat=True))
            for post in posts_results:
                post.is_liked_by_user = post.id in liked_ids
    else:
        posts_results = list(Post.objects.annotate(
            num_likes=Count('likes')
        ).order_by('-num_likes', '-created_at').select_related('user', 'user__profile').prefetch_related('likes', 'comments')[:24])

        if posts_results:
            p_ids = [p.id for p in posts_results]
            liked_ids = set(Like.objects.filter(user=request.user, post_id__in=p_ids).values_list('post_id', flat=True))
            for post in posts_results:
                post.is_liked_by_user = post.id in liked_ids

    context = {
        'query': query,
        'users_results': users_results,
        'posts': posts_results,
    }
    return render(request, 'core/explore.html', context)


@login_required
def notifications_view(request):
    """Notifications feed view - only comments and follows."""
    from ..models import Follow
    notifications = list(
        request.user.notifications.filter(notification_type__in=['comment', 'follow'])
        .select_related('sender', 'sender__profile', 'post')
    )
    
    following_ids = set(
        Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    )
    for n in notifications:
        n.is_following_sender = n.sender_id in following_ids

    # Mark these notifications as read when visited
    request.user.notifications.filter(notification_type__in=['comment', 'follow'], is_read=False).update(is_read=True)
    return render(request, 'core/notifications.html', {'notifications': notifications})
