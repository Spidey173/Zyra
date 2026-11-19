import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models import Post, Conversation, ConversationParticipant
from core.services.messaging import get_or_create_direct_conversation

# Valid 10x10 RGB PNG binary bytes generated via Pillow
TINY_PNG_BYTES = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\n\x00\x00\x00\n\x08\x02\x00\x00\x00\x02PX\xea'
    b'\x00\x00\x00\x13IDATx\x9cc\xfc\xcf\x80\x0f0\xe1\x95e\x18\xa9\xd2\x00A,\x01\x13y\xed\xba&\x00\x00\x00\x00IEND\xaeB`\x82'
)

@pytest.fixture
def user_a(db):
    return User.objects.create_user(username='alice', email='alice@example.com', password='Password123!')

@pytest.fixture
def user_b(db):
    return User.objects.create_user(username='bob', email='bob@example.com', password='Password123!')

@pytest.fixture
def user_c(db):
    return User.objects.create_user(username='charlie', email='charlie@example.com', password='Password123!')

@pytest.fixture
def auth_client_a(user_a):
    client = Client()
    client.force_login(user_a)
    return client

@pytest.fixture
def auth_client_b(user_b):
    client = Client()
    client.force_login(user_b)
    return client

@pytest.fixture
def conversation_ab(user_a, user_b):
    conv, _ = get_or_create_direct_conversation(user_a, user_b)
    return conv

@pytest.fixture
def sample_image():
    return SimpleUploadedFile("test_photo.png", TINY_PNG_BYTES, content_type="image/png")

@pytest.fixture
def sample_video():
    return SimpleUploadedFile("test_clip.mp4", b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom", content_type="video/mp4")

@pytest.fixture(autouse=True)
def configure_test_settings(settings):
    """Ensure tests always use fast in-memory caching and channel layers."""
    settings.CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'zyra-test-cache',
        }
    }
    settings.CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        }
    }
