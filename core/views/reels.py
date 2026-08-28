from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from ..models import Post, Bookmark

@login_required
def reels_view(request):
    """Instagram-style Reels feed with vertical snap-scrolling videos."""
    reels = Post.objects.exclude(video='').exclude(video__isnull=True).select_related('user', 'user__profile').prefetch_related('likes', 'comments')
    for post in reels:
        post.is_liked_by_user = post.likes.filter(user=request.user).exists()
        post.is_bookmarked_by_user = Bookmark.objects.filter(user=request.user, post=post).exists()

    return render(request, 'core/reels.html', {'posts': reels})
