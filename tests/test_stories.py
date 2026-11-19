import pytest
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models import Story
from tests.conftest import TINY_PNG_BYTES

@pytest.mark.django_db
def test_create_story_success(auth_client_a, user_a):
    url = reverse('create_story')
    img = SimpleUploadedFile("story.png", TINY_PNG_BYTES, content_type="image/png")
    payload = {
        'caption': 'My epic story',
        'image': img
    }
    response = auth_client_a.post(url, payload)
    assert response.status_code == 302
    assert Story.objects.filter(user=user_a, caption='My epic story').exists()
    story = Story.objects.get(user=user_a, caption='My epic story')
    assert story.image is not None

@pytest.mark.django_db
def test_create_story_requires_photo_or_video(auth_client_a, user_a):
    url = reverse('create_story')
    payload = {'caption': 'Story without media'}
    response = auth_client_a.post(url, payload)
    assert response.status_code == 302
    assert not Story.objects.filter(user=user_a).exists()

@pytest.mark.django_db
def test_story_24h_expiry_query(user_a):
    # Active story: created 1 hour ago
    s_active = Story.objects.create(user=user_a, caption='Active Story')
    Story.objects.filter(id=s_active.id).update(created_at=timezone.now() - timedelta(hours=1))

    # Expired story: created 25 hours ago
    s_expired = Story.objects.create(user=user_a, caption='Expired Story')
    Story.objects.filter(id=s_expired.id).update(created_at=timezone.now() - timedelta(hours=25))

    # Active stories query (matches feed logic)
    cutoff = timezone.now() - timedelta(hours=24)
    active_qs = Story.objects.filter(created_at__gte=cutoff)

    assert active_qs.filter(id=s_active.id).exists()
    assert not active_qs.filter(id=s_expired.id).exists()

@pytest.mark.django_db
def test_delete_story_author_permission(auth_client_a, user_a):
    story = Story.objects.create(user=user_a, caption='To delete')
    url = reverse('delete_story', kwargs={'story_id': story.id})
    response = auth_client_a.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert response.status_code == 200
    assert response.json()['success'] is True
    assert not Story.objects.filter(id=story.id).exists()

@pytest.mark.django_db
def test_delete_story_non_author_forbidden(auth_client_b, user_a):
    story = Story.objects.create(user=user_a, caption='Alice story')
    url = reverse('delete_story', kwargs={'story_id': story.id})
    response = auth_client_b.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert response.status_code == 403
    assert Story.objects.filter(id=story.id).exists()

@pytest.mark.django_db
def test_stories_rendered_on_feed(auth_client_a, user_a):
    Story.objects.create(user=user_a, caption='Feed Story')
    response = auth_client_a.get(reverse('home'))
    assert response.status_code == 200
    assert len(response.context['story_users']) >= 1

