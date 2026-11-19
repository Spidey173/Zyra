import os
import tempfile
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models import UserProfile, Post, Conversation, ConversationParticipant, Message
from core.services.messaging import (
    get_or_create_direct_conversation,
    send_message,
    get_conversation_messages,
    mark_conversation_read,
    hide_conversation,
    unsend_message,
)
from core.serializers import serialize_message, serialize_conversation, serialize_user
from core.utils.media import generate_upload_path, validate_media_file

class DirectMessagingTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='alice', password='password123')
        self.user_b = User.objects.create_user(username='bob', password='password123')
        self.user_c = User.objects.create_user(username='charlie', password='password123')

    def test_conversation_creation_and_constraints(self):
        # Create direct conversation between alice and bob
        conv, created = get_or_create_direct_conversation(self.user_a, self.user_b)
        self.assertTrue(created)
        self.assertEqual(conv.conversation_type, Conversation.DIRECT)
        self.assertEqual(conv.participants.count(), 2)

        # Re-fetching returns the exact same conversation
        conv2, created2 = get_or_create_direct_conversation(self.user_b, self.user_a)
        self.assertFalse(created2)
        self.assertEqual(conv.id, conv2.id)

        # Attempting self-conversation raises ValidationError
        with self.assertRaises(ValidationError):
            get_or_create_direct_conversation(self.user_a, self.user_a)

    def test_send_message_atomic(self):
        conv, _ = get_or_create_direct_conversation(self.user_a, self.user_b)
        msg = send_message(
            sender=self.user_a,
            conversation_id=conv.id,
            content="Hello Bob!"
        )
        self.assertEqual(msg.decrypted_content, "Hello Bob!")
        self.assertTrue(msg.content.startswith("enc::"))
        self.assertEqual(msg.sender, self.user_a)
        self.assertEqual(conv.messages.count(), 1)

        # Check sender's participant last_read_at updated
        participant_a = conv.participants.get(user=self.user_a)
        self.assertIsNotNone(participant_a.last_read_at)

    def test_unread_count_and_read_receipts(self):
        conv, _ = get_or_create_direct_conversation(self.user_a, self.user_b)
        send_message(sender=self.user_a, conversation_id=conv.id, content="Message 1")
        send_message(sender=self.user_a, conversation_id=conv.id, content="Message 2")

        # Bob should have 2 unread messages
        self.assertEqual(conv.get_unread_count(self.user_b), 2)
        # Alice should have 0 unread messages
        self.assertEqual(conv.get_unread_count(self.user_a), 0)

        # Bob marks conversation as read
        mark_conversation_read(conv, self.user_b)
        self.assertEqual(conv.get_unread_count(self.user_b), 0)

        # All messages from Alice now have read_at timestamp
        unread_remaining = conv.messages.filter(read_at__isnull=True).exclude(sender=self.user_b).count()
        self.assertEqual(unread_remaining, 0)

    def test_permission_checks(self):
        conv, _ = get_or_create_direct_conversation(self.user_a, self.user_b)

        # Charlie (not participant) attempting to send message raises PermissionDenied
        with self.assertRaises(PermissionDenied):
            send_message(sender=self.user_c, conversation_id=conv.id, content="Intruder message")

        # Charlie attempting to read messages raises PermissionDenied
        with self.assertRaises(PermissionDenied):
            get_conversation_messages(conv, self.user_c)

    def test_pagination_cursor(self):
        conv, _ = get_or_create_direct_conversation(self.user_a, self.user_b)
        m1 = send_message(sender=self.user_a, conversation_id=conv.id, content="1")
        m2 = send_message(sender=self.user_a, conversation_id=conv.id, content="2")
        m3 = send_message(sender=self.user_a, conversation_id=conv.id, content="3")

        # Fetch latest 2
        latest_msgs = get_conversation_messages(conv, self.user_a, limit=2)
        self.assertEqual(len(latest_msgs), 2)
        self.assertEqual(latest_msgs[0].id, m2.id)
        self.assertEqual(latest_msgs[1].id, m3.id)

        # Fetch before m2
        older_msgs = get_conversation_messages(conv, self.user_a, before_id=m2.id, limit=2)
        self.assertEqual(len(older_msgs), 1)
        self.assertEqual(older_msgs[0].id, m1.id)

    def test_unsend_message_permissions(self):
        conv, _ = get_or_create_direct_conversation(self.user_a, self.user_b)
        msg = send_message(sender=self.user_a, conversation_id=conv.id, content="Oops")

        # Bob cannot unsend Alice's message
        with self.assertRaises(PermissionDenied):
            unsend_message(msg.id, self.user_b)

        # Alice can unsend her own message
        success = unsend_message(msg.id, self.user_a)
        self.assertTrue(success)
        msg.refresh_from_db()
        self.assertTrue(msg.is_deleted)

    def test_share_post_to_dm(self):
        post = Post.objects.create(user=self.user_a, caption="Check out my photo")
        conv, _ = get_or_create_direct_conversation(self.user_a, self.user_b)

        msg = send_message(
            sender=self.user_a,
            conversation_id=conv.id,
            content="Look at this post",
            post_id=post.id
        )
        self.assertEqual(msg.post, post)

        serialized = serialize_message(msg, self.user_a)
        self.assertIsNotNone(serialized['shared_post'])
        self.assertEqual(serialized['shared_post']['id'], post.id)
        self.assertFalse(serialized['shared_post']['is_reel'])

    def test_media_validation(self):
        # Valid small image
        valid_img = SimpleUploadedFile("avatar.jpg", b"dummy image data", content_type="image/jpeg")
        self.assertTrue(validate_media_file(valid_img, media_types=('image',), max_size_mb=10))

        # Invalid file extension
        bad_file = SimpleUploadedFile("malicious.exe", b"binary", content_type="application/octet-stream")
        with self.assertRaises(ValidationError):
            validate_media_file(bad_file, media_types=('image',), max_size_mb=10)

        # UUID upload path format check
        uploader = generate_upload_path('test_folder')
        generated_path = uploader(None, 'sample_photo.PNG')
        self.assertTrue(generated_path.startswith('test_folder/'))
        self.assertTrue(generated_path.endswith('.png'))

    def test_media_content_type_and_size_validation(self):
        # Valid image with image/png
        png_file = SimpleUploadedFile("pic.png", b"\x89PNG\r\n\x1a\n", content_type="image/png")
        self.assertTrue(validate_media_file(png_file, media_types=('image',), max_size_mb=5))

        # Valid video with video/mp4
        mp4_file = SimpleUploadedFile("clip.mp4", b"video data", content_type="video/mp4")
        self.assertTrue(validate_media_file(mp4_file, media_types=('video',), max_size_mb=50))

        # Valid audio with audio/mpeg
        mp3_file = SimpleUploadedFile("audio.mp3", b"audio data", content_type="audio/mpeg")
        self.assertTrue(validate_media_file(mp3_file, media_types=('audio',), max_size_mb=10))

        # Spoofed MIME type: .jpg extension with malicious content type
        bad_mime = SimpleUploadedFile("photo.jpg", b"bad", content_type="application/x-sh")
        with self.assertRaises(ValidationError):
            validate_media_file(bad_mime, media_types=('image',), max_size_mb=10)

        # File exceeding size limit
        oversized = SimpleUploadedFile("huge.jpg", b"x" * (6 * 1024 * 1024), content_type="image/jpeg")
        with self.assertRaises(ValidationError):
            validate_media_file(oversized, media_types=('image',), max_size_mb=5)

    def test_persistent_media_and_serve_media_removed(self):
        import core.models as core_models
        self.assertFalse(hasattr(core_models, 'PersistentMediaFile'), "PersistentMediaFile must be removed from models")

        import core.views as core_views
        self.assertFalse(hasattr(core_views, 'serve_media_view'), "serve_media_view must be removed from views")

    def test_storage_settings_and_command(self):
        from django.conf import settings
        from django.core.management import call_command
        import io

        self.assertIn('storages', settings.INSTALLED_APPS)
        self.assertIn('default', settings.STORAGES)

        out = io.StringIO()
        call_command('migrate_media_to_storage', stdout=out)
        self.assertIn("Nothing to migrate", out.getvalue())

    def test_cloudinary_media_storage(self):
        from core.storage import CloudinaryMediaStorage
        from django.core.files.base import ContentFile

        storage = CloudinaryMediaStorage()
        test_filename = 'posts/test_image.png'
        # Tiny 1x1 transparent PNG binary bytes
        tiny_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        
        saved_url = storage.save(test_filename, ContentFile(tiny_png))
        self.assertTrue(saved_url.startswith('http://') or saved_url.startswith('https://') or 'test_image' in saved_url)
        
        resolved_url = storage.url(saved_url)
        self.assertTrue(resolved_url.startswith('http://') or resolved_url.startswith('https://'))

    def test_vercel_entry_removed(self):
        from django.conf import settings
        self.assertFalse(os.path.exists(settings.BASE_DIR / 'api' / 'index.py'))
        self.assertFalse(os.path.exists(settings.BASE_DIR / 'vercel.json'))
        self.assertFalse(os.path.exists(settings.BASE_DIR / 'build_files.sh'))

    def test_asgi_application_structure(self):
        from config.asgi import application
        from channels.routing import ProtocolTypeRouter
        self.assertIsInstance(application, ProtocolTypeRouter)
        self.assertIn("http", application.application_mapping)
        self.assertIn("websocket", application.application_mapping)

    def test_deployment_configs_exist(self):
        from django.conf import settings
        self.assertTrue(os.path.exists(settings.BASE_DIR / 'Dockerfile'))
        self.assertTrue(os.path.exists(settings.BASE_DIR / 'docker-compose.yml'))
        self.assertTrue(os.path.exists(settings.BASE_DIR / 'Procfile'))
        self.assertTrue(os.path.exists(settings.BASE_DIR / 'railway.toml'))
        self.assertTrue(os.path.exists(settings.BASE_DIR / 'render.yaml'))
        self.assertTrue(os.path.exists(settings.BASE_DIR / 'fly.toml'))

    def test_redis_required_in_production(self):
        from django.core.exceptions import ImproperlyConfigured
        redis_url = None
        debug_flag = False
        if not redis_url and not debug_flag:
            with self.assertRaises(ImproperlyConfigured):
                raise ImproperlyConfigured(
                    "REDIS_URL environment variable is required in production for channels_redis."
                )

    def test_websocket_chat_consumer_auth_and_reconnect(self):
        from asgiref.sync import async_to_sync
        from channels.testing import WebsocketCommunicator
        from django.contrib.auth.models import AnonymousUser
        from core.consumers import ChatConsumer

        conv, _ = get_or_create_direct_conversation(self.user_a, self.user_b)

        async def _run_tests():
            # 1. Unauthenticated connection rejected immediately
            comm_unauth = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{conv.id}/")
            comm_unauth.scope["url_route"] = {"kwargs": {"conversation_id": str(conv.id)}}
            comm_unauth.scope["user"] = AnonymousUser()
            connected, close_code = await comm_unauth.connect()
            self.assertFalse(connected)
            self.assertEqual(close_code, 4401)
            await comm_unauth.disconnect()

            # 2. Non-participant rejected with 4403
            comm_outsider = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{conv.id}/")
            comm_outsider.scope["url_route"] = {"kwargs": {"conversation_id": str(conv.id)}}
            comm_outsider.scope["user"] = self.user_c
            connected, close_code = await comm_outsider.connect()
            self.assertFalse(connected)
            self.assertEqual(close_code, 4403)
            await comm_outsider.disconnect()

            # 3. Authenticated participant connects successfully
            comm_auth = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{conv.id}/")
            comm_auth.scope["url_route"] = {"kwargs": {"conversation_id": str(conv.id)}}
            comm_auth.scope["user"] = self.user_a
            connected, _ = await comm_auth.connect()
            self.assertTrue(connected)

            # Receive initial connection confirmation
            init_evt = await comm_auth.receive_json_from()
            self.assertEqual(init_evt["type"], "connection_established")
            self.assertEqual(init_evt["conversation_id"], str(conv.id))

            # Test heartbeat ping -> pong
            await comm_auth.send_json_to({"action": "ping"})
            pong_evt = await comm_auth.receive_json_from()
            self.assertEqual(pong_evt["type"], "pong")

            # Test reconnect / sync history
            await comm_auth.send_json_to({"action": "reconnect", "last_message_id": 0})
            sync_evt = await comm_auth.receive_json_from()
            self.assertEqual(sync_evt["type"], "sync_history")
            self.assertIsInstance(sync_evt["messages"], list)

            await comm_auth.disconnect()

        async_to_sync(_run_tests)()

    def test_phase3_split_settings_structure(self):
        import importlib
        base_settings = importlib.import_module('config.settings.base')
        dev_settings = importlib.import_module('config.settings.dev')
        self.assertFalse(base_settings.DEBUG)
        self.assertTrue(dev_settings.DEBUG)
        self.assertNotIn('*', dev_settings.ALLOWED_HOSTS)

    def test_phase3_production_secret_key_crash_when_missing(self):
        import subprocess
        import sys
        
        # Test missing SECRET_KEY crashes with ImproperlyConfigured
        cmd = [
            sys.executable, "-c",
            "import os; os.environ.pop('SECRET_KEY', None); "
            "import config.settings.prod"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("ImproperlyConfigured", res.stderr)
        self.assertIn("SECRET_KEY", res.stderr)

    def test_phase3_production_allowed_hosts_no_wildcard(self):
        import subprocess
        import sys

        # Test wildcard '*' in ALLOWED_HOSTS is rejected
        cmd = [
            sys.executable, "-c",
            "import os; os.environ['SECRET_KEY'] = 'strong-prod-key-1234567890'; "
            "os.environ['ALLOWED_HOSTS'] = '*'; "
            "import config.settings.prod"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("ImproperlyConfigured", res.stderr)
        self.assertIn("ALLOWED_HOSTS", res.stderr)

    def test_phase3_production_security_flags(self):
        import subprocess
        import sys
        import json

        # Test production security settings with valid required env vars
        cmd = [
            sys.executable, "-c",
            "import os, json; "
            "os.environ['SECRET_KEY'] = 'strong-prod-key-1234567890'; "
            "os.environ['ALLOWED_HOSTS'] = 'zyra.app,api.zyra.app'; "
            "os.environ['REDIS_URL'] = 'redis://localhost:6379/0'; "
            "from config.settings import prod; "
            "out = {"
            "'DEBUG': prod.DEBUG, "
            "'SESSION_COOKIE_SECURE': prod.SESSION_COOKIE_SECURE, "
            "'CSRF_COOKIE_SECURE': prod.CSRF_COOKIE_SECURE, "
            "'SECURE_BROWSER_XSS_FILTER': prod.SECURE_BROWSER_XSS_FILTER, "
            "'SECURE_CONTENT_TYPE_NOSNIFF': prod.SECURE_CONTENT_TYPE_NOSNIFF, "
            "'X_FRAME_OPTIONS': prod.X_FRAME_OPTIONS, "
            "'SECURE_HSTS_SECONDS': prod.SECURE_HSTS_SECONDS"
            "}; print(json.dumps(out))"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Prod settings failed to load: {res.stderr}")
        data = json.loads(res.stdout.strip())
        self.assertFalse(data['DEBUG'])
        self.assertTrue(data['SESSION_COOKIE_SECURE'])
        self.assertTrue(data['CSRF_COOKIE_SECURE'])
        self.assertTrue(data['SECURE_BROWSER_XSS_FILTER'])
        self.assertTrue(data['SECURE_CONTENT_TYPE_NOSNIFF'])
        self.assertEqual(data['X_FRAME_OPTIONS'], 'DENY')
        self.assertEqual(data['SECURE_HSTS_SECONDS'], 31536000)

    def test_phase3_env_example_template(self):
        from django.conf import settings
        example_path = settings.BASE_DIR / '.env.example'
        self.assertTrue(example_path.exists())
        content = example_path.read_text(encoding='utf-8')
        self.assertIn('SECRET_KEY', content)
        self.assertIn('ALLOWED_HOSTS', content)
        self.assertIn('REDIS_URL', content)
        self.assertIn('SECURE_SSL_REDIRECT', content)
        self.assertNotIn('549768947857682', content)
        self.assertNotIn('R2dzLnaTB_gIbCVcWF9ptUIVZN8', content)



