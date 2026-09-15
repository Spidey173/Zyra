import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from ..models import UserProfile, Post, Like, Follow, Bookmark, Notification
from ..forms import UserProfileForm
from ..utils.rate_limit import rate_limit

@login_required
@rate_limit('edit_profile', limit=15, period=60)
def user_profile(request, username):
    """User profile page with grid tabs (Posts, Reels, Saved) and Edit Profile modal."""
    profile_user = get_object_or_404(User.objects.select_related('profile'), username=username)
    profile_user.profile.cached_followers_count = Follow.objects.filter(following=profile_user).count()
    profile_user.profile.cached_following_count = Follow.objects.filter(follower=profile_user).count()
    posts = profile_user.posts.all().prefetch_related('likes', 'comments')
    
    is_following = Follow.objects.filter(follower=request.user, following=profile_user).exists()
    is_self = (request.user == profile_user)

    profile_form = None
    if is_self:
        if request.method == 'POST':
            if request.POST.get('action') == 'remove_photo':
                if profile_user.profile.profile_pic:
                    profile_user.profile.profile_pic.delete(save=False)
                    profile_user.profile.profile_pic = None
                    profile_user.profile.save()
                messages.success(request, "Profile photo removed.")
                return redirect('user_profile', username=username)
            new_username = request.POST.get('username', '').strip()
            if new_username and new_username != profile_user.username:
                if not re.match(r'^[\w.@+-]+$', new_username):
                    messages.error(request, "Username may only contain letters, numbers, and @/./+/-/_ characters.")
                elif len(new_username) < 3 or len(new_username) > 30:
                    messages.error(request, "Username must be between 3 and 30 characters.")
                elif User.objects.filter(username__iexact=new_username).exclude(id=profile_user.id).exists():
                    messages.error(request, "Username already taken.")
                else:
                    profile_user.username = new_username
                    profile_user.save()
                    username = new_username

            profile_form = UserProfileForm(request.POST, request.FILES, instance=profile_user.profile)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profile updated successfully!")
                return redirect('user_profile', username=username)
        else:
            profile_form = UserProfileForm(instance=profile_user.profile)

    saved_posts = []
    if is_self:
        saved_posts = list(Post.objects.filter(bookmarks__user=profile_user).select_related('user', 'user__profile').prefetch_related('likes', 'comments'))

    posts_list = list(posts)
    # User's video reels
    user_reels = [p for p in posts_list if p.video]

    all_profile_posts = set(posts_list + saved_posts)
    all_post_ids = [p.id for p in all_profile_posts]
    user_liked_ids = set(Like.objects.filter(user=request.user, post_id__in=all_post_ids).values_list('post_id', flat=True))
    user_saved_ids = set(Bookmark.objects.filter(user=request.user, post_id__in=all_post_ids).values_list('post_id', flat=True))

    for post in posts_list:
        post.is_liked_by_user = post.id in user_liked_ids
        post.is_bookmarked_by_user = post.id in user_saved_ids

    for post in saved_posts:
        post.is_liked_by_user = post.id in user_liked_ids
        post.is_bookmarked_by_user = True

    context = {
        'profile_user': profile_user,
        'posts': posts,
        'user_reels': user_reels,
        'saved_posts': saved_posts,
        'is_following': is_following,
        'is_self': is_self,
        'profile_form': profile_form,
    }
    return render(request, 'core/user_profile.html', context)


@login_required
@require_POST
@rate_limit('follow', limit=60, period=60, is_json=True)
def follow_user(request, username):
    """Follow / Unfollow toggle with AJAX support."""
    target_user = get_object_or_404(User, username=username)
    is_following = False
    if target_user != request.user:
        follow, created = Follow.objects.get_or_create(follower=request.user, following=target_user)
        if not created:
            follow.delete()
            is_following = False
        else:
            is_following = True
            Notification.objects.get_or_create(
                sender=request.user, receiver=target_user, notification_type='follow'
            )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'following': is_following,
            'followers_count': target_user.profile.followers_count,
            'following_count': target_user.profile.following_count
        })

    next_url = request.META.get('HTTP_REFERER')
    if next_url and 'user' in next_url:
        return redirect('user_profile', username=username)
    return redirect(next_url if next_url else 'home')


@login_required
def followers_list(request, username):
    """Followers list view."""
    profile_user = get_object_or_404(User, username=username)
    followers = list(Follow.objects.filter(following=profile_user).select_related('follower', 'follower__profile'))
    follower_target_ids = [f.follower_id for f in followers]
    user_following_ids = set(
        Follow.objects.filter(follower=request.user, following_id__in=follower_target_ids).values_list('following_id', flat=True)
    )

    for follow in followers:
        follow.follower.is_followed_by_user = follow.follower_id in user_following_ids

    context = {
        'profile_user': profile_user,
        'followers': followers,
    }
    return render(request, 'core/followers_list.html', context)


@login_required
def following_list(request, username):
    """Following list view."""
    profile_user = get_object_or_404(User, username=username)
    following_relations = list(Follow.objects.filter(follower=profile_user).select_related('following', 'following__profile'))
    following_target_ids = [r.following_id for r in following_relations]
    user_following_ids = set(
        Follow.objects.filter(follower=request.user, following_id__in=following_target_ids).values_list('following_id', flat=True)
    )

    for relation in following_relations:
        relation.following.is_followed_by_user = relation.following_id in user_following_ids

    context = {
        'profile_user': profile_user,
        'following_relations': following_relations,
    }
    return render(request, 'core/following_list.html', context)
