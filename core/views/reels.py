from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from ..models import Post, Like, Bookmark

@login_required
def reels_view(request):
    """Instagram-style Reels feed with vertical snap-scrolling videos."""
    reels = list(Post.objects.exclude(video='').exclude(video__isnull=True).select_related('user', 'user__profile').prefetch_related('likes', 'comments'))
    reel_ids = [p.id for p in reels]
    user_liked = set(Like.objects.filter(user=request.user, post_id__in=reel_ids).values_list('post_id', flat=True))
    user_bookmarked = set(Bookmark.objects.filter(user=request.user, post_id__in=reel_ids).values_list('post_id', flat=True))
    for post in reels:
        post.is_liked_by_user = post.id in user_liked
        post.is_bookmarked_by_user = post.id in user_bookmarked

    return render(request, 'core/reels.html', {'posts': reels})
