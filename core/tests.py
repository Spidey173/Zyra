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

    def test_persistent_media_storage_and_recovery(self):
        from core.models import PersistentMediaFile
        from core.storage import ResilientMediaStorage
        from django.core.files.base import ContentFile
        import tempfile
        import shutil

        storage = ResilientMediaStorage()
        test_filename = 'test_reels/sample_reel.mp4'
        test_data = b'fake mp4 video binary content 12345'

        # 1. Save via storage
        saved_name = storage.save(test_filename, ContentFile(test_data))
        self.assertTrue(storage.exists(saved_name))

        # 2. Check that it was saved to DB
        stored = PersistentMediaFile.objects.filter(file_path=saved_name).first()
        self.assertIsNotNone(stored)
        self.assertEqual(stored.data, test_data)

        # 3. Simulate disk wipe (like Render container restart)
        full_path = storage.path(saved_name)
        if os.path.exists(full_path):
            os.remove(full_path)
        self.assertFalse(os.path.exists(full_path))

        # 4. Request via storage or serve_media_view - it should automatically restore
        client_response = self.client.get(f'/media/{saved_name}')
        self.assertEqual(client_response.status_code, 200)
        self.assertTrue(os.path.exists(full_path))
        with open(full_path, 'rb') as f:
            self.assertEqual(f.read(), test_data)

