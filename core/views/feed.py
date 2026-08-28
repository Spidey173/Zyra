import json
import datetime
from collections import defaultdict
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from ..models import Post, Like, Comment, Follow, Bookmark, Notification, Story
from ..forms import PostForm, CommentForm
from ..utils.media import get_media_url

@login_required
def home(request):
    """Main feed view with Instagram-style stories, post stream, and user suggestions."""
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.save()
            messages.success(request, "Post published successfully!")
            return redirect('home')
    else:
        form = PostForm()

    # Followed users
    followed_users = Follow.objects.filter(follower=request.user).values_list('following', flat=True)

    # Query feed posts (own + followed)
    posts = Post.objects.filter(
        Q(user__in=followed_users) | Q(user=request.user)
    ).select_related('user', 'user__profile').prefetch_related('likes', 'comments')

    # Fallback to all posts if feed is empty
    if not posts.exists():
        posts = Post.objects.all().select_related('user', 'user__profile').prefetch_related('likes', 'comments')

    # Pagination for infinite scroll (5 per page)
    paginator = Paginator(posts, 5)
    page = request.GET.get('page')
    try:
        posts_page = paginator.page(page)
    except PageNotAnInteger:
        posts_page = paginator.page(1)
    except EmptyPage:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'posts_html': ''})
        posts_page = paginator.page(paginator.num_pages)

    # Batch interaction flags to avoid N+1 database queries
    post_ids = [p.id for p in posts_page]
    user_liked_post_ids = set(Like.objects.filter(user=request.user, post_id__in=post_ids).values_list('post_id', flat=True))
    user_bookmarked_post_ids = set(Bookmark.objects.filter(user=request.user, post_id__in=post_ids).values_list('post_id', flat=True))
    for post in posts_page:
        post.is_liked_by_user = post.id in user_liked_post_ids
        post.is_bookmarked_by_user = post.id in user_bookmarked_post_ids

    # Dynamic suggestions (not followed & not self)
    suggested_users = User.objects.exclude(
        id__in=followed_users
    ).exclude(id=request.user.id).select_related('profile')[:5]

    # Stories active in last 24h
    active_stories = Story.objects.filter(
        created_at__gte=timezone.now() - datetime.timedelta(hours=24)
    ).select_related('user', 'user__profile').order_by('created_at')

    stories_by_user = defaultdict(list)
    for story in active_stories:
        stories_by_user[story.user].append({
            'id': story.id,
            'image_url': story.get_image_url,
            'video_url': story.get_video_url,
            'music_url': story.get_music_url,
            'caption': story.caption,
            'created_at': story.created_at.strftime('%I:%M %p')
        })

    story_bubbles = []
    story_bubbles_json = []
    for s_user, user_stories in stories_by_user.items():
        story_bubbles.append({
            'user': s_user,
            'stories': user_stories
        })
        story_bubbles_json.append({
            'username': s_user.username,
            'profile_pic': get_media_url(s_user.profile.profile_pic) if hasattr(s_user, 'profile') else None,
            'stories': user_stories
        })

    # AJAX scroll request -> partial template
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'core/post_list_partial.html', {'posts': posts_page})

    context = {
        'form': form,
        'posts': posts_page,
        'suggested_users': suggested_users,
        'story_users': story_bubbles,
        'story_bubbles_json': json.dumps(story_bubbles_json),
    }
    return render(request, 'core/home.html', context)


@login_required
def post_detail(request, post_id):
    """Post detail modal/page with comment thread."""
    post = get_object_or_404(Post.objects.select_related('user', 'user__profile'), id=post_id)
    comments = post.comments.select_related('user', 'user__profile')
    is_liked = post.likes.filter(user=request.user).exists()
    is_bookmarked = Bookmark.objects.filter(user=request.user, post=post).exists()

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.post = post
            comment.save()

            if post.user != request.user:
                Notification.objects.create(
                    sender=request.user, receiver=post.user, post=post, notification_type='comment'
                )

            messages.success(request, "Comment added.")
            return redirect('post_detail', post_id=post.id)
    else:
        form = CommentForm()

    context = {
        'post': post,
        'comments': comments,
        'is_liked': is_liked,
        'is_bookmarked': is_bookmarked,
        'form': form,
    }
    return render(request, 'core/post_detail.html', context)


@login_required
def like_post(request, post_id):
    """Toggle like on post with AJAX support."""
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        like, created = Like.objects.get_or_create(user=request.user, post=post)
        if not created:
            like.delete()
            liked = False
        else:
            liked = True
            if post.user != request.user:
                Notification.objects.get_or_create(
                    sender=request.user, receiver=post.user, post=post, notification_type='like'
                )

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'liked': liked,
                'likes_count': post.likes_count
            })

        next_url = request.META.get('HTTP_REFERER', 'home')
        return redirect(next_url)
    return redirect('home')


@login_required
def comment_post(request, post_id):
    """Add a comment with AJAX response."""
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.post = post
            comment.save()

            if post.user != request.user:
                Notification.objects.create(
                    sender=request.user, receiver=post.user, post=post, notification_type='comment'
                )

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'comment': {
                        'id': comment.id,
                        'username': comment.user.username,
                        'user_url': f'/user/{comment.user.username}/',
                        'profile_pic': get_media_url(comment.user.profile.profile_pic) if hasattr(comment.user, 'profile') else None,
                        'content': comment.content,
                        'created_at': 'Just now'
                    }
                })
            messages.success(request, "Comment added.")
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)

        next_url = request.META.get('HTTP_REFERER', 'post_detail')
        if next_url == 'post_detail':
            return redirect('post_detail', post_id=post.id)
        return redirect(next_url)
    return redirect('home')


@login_required
def toggle_bookmark(request, post_id):
    """Toggle save/bookmark on a post."""
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        bookmark, created = Bookmark.objects.get_or_create(user=request.user, post=post)
        if not created:
            bookmark.delete()
            bookmarked = False
        else:
            bookmarked = True

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'bookmarked': bookmarked})

        return redirect(request.META.get('HTTP_REFERER', 'home'))
    return redirect('home')


@login_required
def delete_post(request, post_id):
    """Delete a post owned by the request user."""
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        if post.user == request.user:
            post.delete()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            messages.success(request, "Post deleted successfully.")
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
            messages.error(request, "You cannot delete this post.")
    return redirect('home')


@login_required
def delete_comment(request, comment_id):
    """Delete a comment (allowed for comment author or post owner)."""
    if request.method == 'POST':
        comment = get_object_or_404(Comment, id=comment_id)
        if comment.user != request.user and comment.post.user != request.user:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
            return HttpResponseForbidden("You are not allowed to delete this comment.")

        post_id = comment.post.id
        # Remove related notification if any
        Notification.objects.filter(post=comment.post, sender=comment.user, notification_type='comment').delete()
        comment.delete()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'comment_id': comment_id})

        return redirect('post_detail', post_id=post_id)
    return redirect('home')
