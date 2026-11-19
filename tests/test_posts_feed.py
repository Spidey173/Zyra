import pytest
from django.urls import reverse
from core.models import Post, Follow
from tests.conftest import TINY_PNG_BYTES
from django.core.files.uploadedfile import SimpleUploadedFile

@pytest.mark.django_db
def test_create_post_with_image(auth_client_a, user_a):
    url = reverse('home')
    img = SimpleUploadedFile("feed_pic.png", TINY_PNG_BYTES, content_type="image/png")
    payload = {
        'caption': 'Hello Zyra World!',
        'image': img
    }
    response = auth_client_a.post(url, payload)
    assert response.status_code == 302
    assert Post.objects.filter(user=user_a, caption='Hello Zyra World!').exists()
    post = Post.objects.get(user=user_a, caption='Hello Zyra World!')
    assert post.image is not None

@pytest.mark.django_db
def test_create_post_requires_content_or_media(auth_client_a):
    url = reverse('home')
    payload = {'caption': '', 'image': '', 'video': ''}
    response = auth_client_a.post(url, payload)
    # Form fails validation and renders page again
    assert response.status_code == 200
    assert Post.objects.count() == 0

@pytest.mark.django_db
def test_feed_ordering_chronological(auth_client_a, user_a):
    p1 = Post.objects.create(user=user_a, caption='First Post')
    p2 = Post.objects.create(user=user_a, caption='Second Post')
    p3 = Post.objects.create(user=user_a, caption='Third Post')

    response = auth_client_a.get(reverse('home'))
    assert response.status_code == 200
    posts = list(response.context['posts'])
    assert posts[0].id == p3.id
    assert posts[1].id == p2.id
    assert posts[2].id == p1.id

@pytest.mark.django_db
def test_feed_filtered_by_following(auth_client_a, user_a, user_b, user_c):
    # user_a follows user_b, but does NOT follow user_c
    Follow.objects.create(follower=user_a, following=user_b)
    
    post_self = Post.objects.create(user=user_a, caption='My post')
    post_b = Post.objects.create(user=user_b, caption='Bob post')
    post_c = Post.objects.create(user=user_c, caption='Charlie post')

    response = auth_client_a.get(reverse('home'))
    posts = list(response.context['posts'])
    post_ids = [p.id for p in posts]
    
    assert post_self.id in post_ids
    assert post_b.id in post_ids
    assert post_c.id not in post_ids

@pytest.mark.django_db
def test_feed_pagination(auth_client_a, user_a):
    for i in range(12):
        Post.objects.create(user=user_a, caption=f"Post #{i}")

    # First page should contain 5 posts
    resp_p1 = auth_client_a.get(reverse('home') + '?page=1')
    assert len(resp_p1.context['posts']) == 5
    assert resp_p1.context['posts'].has_next()

    # Second page should contain 5 posts
    resp_p2 = auth_client_a.get(reverse('home') + '?page=2')
    assert len(resp_p2.context['posts']) == 5

    # Third page should contain 2 posts
    resp_p3 = auth_client_a.get(reverse('home') + '?page=3')
    assert len(resp_p3.context['posts']) == 2
    assert not resp_p3.context['posts'].has_next()

@pytest.mark.django_db
def test_delete_post_author_permission(auth_client_a, user_a):
    post = Post.objects.create(user=user_a, caption='To be deleted')
    url = reverse('delete_post', kwargs={'post_id': post.id})
    response = auth_client_a.post(url)
    assert response.status_code == 302
    assert not Post.objects.filter(id=post.id).exists()

@pytest.mark.django_db
def test_delete_post_non_author_forbidden(auth_client_b, user_a):
    post = Post.objects.create(user=user_a, caption='Alice post')
    url = reverse('delete_post', kwargs={'post_id': post.id})
    # Bob attempts to delete Alice's post via AJAX -> 403 Forbidden
    response = auth_client_b.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert response.status_code == 403
    assert Post.objects.filter(id=post.id).exists()

@pytest.mark.django_db
def test_post_detail_view(auth_client_a, user_a):
    post = Post.objects.create(user=user_a, caption='Detailed post discussion')
    url = reverse('post_detail', kwargs={'post_id': post.id})
    response = auth_client_a.get(url)
    assert response.status_code == 200
    assert 'Detailed post discussion' in response.content.decode('utf-8')
