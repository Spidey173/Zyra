import pytest
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from core.models import Post
from core.utils.media import validate_media_file

@pytest.mark.django_db
def test_reels_view_authenticated(auth_client_a, user_a):
    url = reverse('reels')
    response = auth_client_a.get(url)
    assert response.status_code == 200
    assert 'posts' in response.context

@pytest.mark.django_db
def test_reels_view_unauthenticated(client):
    url = reverse('reels')
    response = client.get(url)
    assert response.status_code == 302
    assert reverse('login') in response.url

@pytest.mark.django_db
def test_reels_feed_filters_only_videos(auth_client_a, user_a):
    # Post with video (reel)
    reel_post = Post.objects.create(user=user_a, caption='Reel post', video='reels/clip.mp4')
    # Post with only image (not reel)
    image_post = Post.objects.create(user=user_a, caption='Image post', image='posts/pic.jpg')

    response = auth_client_a.get(reverse('reels'))
    assert response.status_code == 200
    reels = list(response.context['posts'])
    reel_ids = [r.id for r in reels]

    assert reel_post.id in reel_ids
    assert image_post.id not in reel_ids

def test_reel_validation_valid_video():
    valid_video = SimpleUploadedFile("reel.mp4", b"\x00\x00\x00\x18ftypmp42", content_type="video/mp4")
    assert validate_media_file(valid_video, media_types=('video',), max_size_mb=50) is True

def test_reel_validation_invalid_extension():
    bad_file = SimpleUploadedFile("malicious.exe", b"MZ\x90\x00", content_type="video/mp4")
    with pytest.raises(ValidationError) as exc:
        validate_media_file(bad_file, media_types=('video',), max_size_mb=50)
    assert "Unsupported file extension" in str(exc.value)

def test_reel_validation_invalid_mimetype():
    bad_mime = SimpleUploadedFile("video.mp4", b"\x00\x00", content_type="application/x-msdownload")
    with pytest.raises(ValidationError) as exc:
        validate_media_file(bad_mime, media_types=('video',), max_size_mb=50)
    assert "Unsupported content-type" in str(exc.value)

def test_reel_validation_oversized():
    # 51MB mock file
    huge_payload = b"0" * (51 * 1024 * 1024)
    huge_file = SimpleUploadedFile("big_video.mp4", huge_payload, content_type="video/mp4")
    with pytest.raises(ValidationError) as exc:
        validate_media_file(huge_file, media_types=('video',), max_size_mb=50)
    assert "exceeds maximum allowed limit" in str(exc.value)

