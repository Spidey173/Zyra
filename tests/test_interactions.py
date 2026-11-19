import pytest
from django.urls import reverse
from core.models import Post, Like, Comment, Bookmark, Follow

@pytest.mark.django_db
def test_like_toggle_post(auth_client_a, user_a, user_b):
    post = Post.objects.create(user=user_b, caption='Post to like')
    url = reverse('like_post', kwargs={'post_id': post.id})

    # 1. Like the post (AJAX)
    resp1 = auth_client_a.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1['liked'] is True
    assert data1['likes_count'] == 1
    assert Like.objects.filter(user=user_a, post=post).exists()

    # 2. Toggle unlike (AJAX)
    resp2 = auth_client_a.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2['liked'] is False
    assert data2['likes_count'] == 0
    assert not Like.objects.filter(user=user_a, post=post).exists()

@pytest.mark.django_db
def test_like_unique_constraint(user_a, user_b):
    post = Post.objects.create(user=user_b, caption='Unique like test')
    Like.objects.create(user=user_a, post=post)
    with pytest.raises(Exception):
        Like.objects.create(user=user_a, post=post)

@pytest.mark.django_db
def test_comment_creation(auth_client_a, user_a, user_b):
    post = Post.objects.create(user=user_b, caption='Comment on me')
    url = reverse('comment_post', kwargs={'post_id': post.id})
    resp = auth_client_a.post(url, {'content': 'Great photo!'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert resp.status_code == 200
    data = resp.json()
    assert data['success'] is True
    assert data['comment']['content'] == 'Great photo!'
    assert Comment.objects.filter(post=post, user=user_a, content='Great photo!').exists()

@pytest.mark.django_db
def test_comment_author_delete(auth_client_a, user_a, user_b):
    post = Post.objects.create(user=user_b, caption='Post')
    comment = Comment.objects.create(user=user_a, post=post, content='My comment to delete')
    url = reverse('delete_comment', kwargs={'comment_id': comment.id})

    resp = auth_client_a.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert resp.status_code == 200
    assert resp.json()['success'] is True
    assert not Comment.objects.filter(id=comment.id).exists()

@pytest.mark.django_db
def test_post_owner_delete_comment(auth_client_b, user_a, user_b):
    # Bob owns post; Alice comments on it; Bob can delete Alice's comment
    post = Post.objects.create(user=user_b, caption='Bob post')
    comment = Comment.objects.create(user=user_a, post=post, content='Spam comment')
    url = reverse('delete_comment', kwargs={'comment_id': comment.id})

    resp = auth_client_b.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert resp.status_code == 200
    assert not Comment.objects.filter(id=comment.id).exists()

@pytest.mark.django_db
def test_unauthorized_user_cannot_delete_comment(auth_client_b, user_a, user_c):
    # Post by Charlie, comment by Alice; Bob cannot delete it
    post = Post.objects.create(user=user_c, caption='Charlie post')
    comment = Comment.objects.create(user=user_a, post=post, content='Alice comment')
    url = reverse('delete_comment', kwargs={'comment_id': comment.id})

    resp = auth_client_b.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert resp.status_code == 403
    assert Comment.objects.filter(id=comment.id).exists()

@pytest.mark.django_db
def test_bookmark_toggle(auth_client_a, user_a, user_b):
    post = Post.objects.create(user=user_b, caption='Post to bookmark')
    url = reverse('toggle_bookmark', kwargs={'post_id': post.id})

    # Bookmark (AJAX)
    resp1 = auth_client_a.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert resp1.status_code == 200
    assert resp1.json()['bookmarked'] is True
    assert Bookmark.objects.filter(user=user_a, post=post).exists()

    # Un-bookmark (AJAX)
    resp2 = auth_client_a.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert resp2.status_code == 200
    assert resp2.json()['bookmarked'] is False
    assert not Bookmark.objects.filter(user=user_a, post=post).exists()

@pytest.mark.django_db
def test_follow_unfollow_user(auth_client_a, user_a, user_b):
    url = reverse('follow_user', kwargs={'username': user_b.username})

    # Follow
    resp1 = auth_client_a.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert resp1.status_code == 200
    assert resp1.json()['following'] is True
    assert Follow.objects.filter(follower=user_a, following=user_b).exists()

    # Unfollow
    resp2 = auth_client_a.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert resp2.status_code == 200
    assert resp2.json()['following'] is False
    assert not Follow.objects.filter(follower=user_a, following=user_b).exists()
