from datetime import timedelta
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from .utils.media import generate_upload_path, get_media_url

class UserProfile(models.Model):
    GENDER_CHOICES = [
        ('he/him', 'Boy (he/him)'),
        ('she/her', 'Girl (she/her)'),
        ('they/them', 'They (they/them)'),
        ('none', 'Prefer not to say'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=30, choices=GENDER_CHOICES, default='he/him', blank=True)
    bio = models.TextField(max_length=500, blank=True)
    profile_pic = models.ImageField(upload_to=generate_upload_path('avatars'), blank=True, null=True)
    last_seen = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['last_seen']),
        ]

    def __str__(self):
        return f"{self.user.username}'s profile"

    @property
    def followers_count(self):
        if hasattr(self, 'cached_followers_count'):
            return self.cached_followers_count
        return Follow.objects.filter(following=self.user).count()

    @property
    def following_count(self):
        if hasattr(self, 'cached_following_count'):
            return self.cached_following_count
        return Follow.objects.filter(follower=self.user).count()

    @property
    def get_profile_pic_url(self):
        return get_media_url(self.profile_pic)

    @property
    def is_online(self):
        if not self.last_seen:
            return False
        return timezone.now() - self.last_seen <= timedelta(minutes=3)

    @property
    def online_status_text(self):
        if not self.last_seen:
            return "Offline"
        diff = timezone.now() - self.last_seen
        minutes = int(diff.total_seconds() // 60)
        if minutes < 3:
            return "Active now"
        elif minutes < 60:
            return f"Active {minutes}m ago"
        elif minutes < 1440:
            hours = minutes // 60
            return f"Active {hours}h ago"
        else:
            days = minutes // 1440
            return f"Active {days}d ago" if days < 7 else "Offline"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        UserProfile.objects.create(user=instance)


class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    caption = models.TextField(max_length=1000, blank=True)
    image = models.ImageField(upload_to=generate_upload_path('posts'), blank=True, null=True)
    video = models.FileField(upload_to=generate_upload_path('reels'), blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"Post by {self.user.username} at {self.created_at}"

    @property
    def likes_count(self):
        if hasattr(self, 'cached_likes_count'):
            return self.cached_likes_count
        if hasattr(self, '_prefetched_objects_cache') and 'likes' in self._prefetched_objects_cache:
            return len(self.likes.all())
        return self.likes.count()

    @property
    def comments_count(self):
        if hasattr(self, 'cached_comments_count'):
            return self.cached_comments_count
        if hasattr(self, '_prefetched_objects_cache') and 'comments' in self._prefetched_objects_cache:
            return len(self.comments.all())
        return self.comments.count()

    @property
    def get_image_url(self):
        return get_media_url(self.image)

    @property
    def get_video_url(self):
        return get_media_url(self.video)


class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')
        indexes = [
            models.Index(fields=['user', 'post']),
            models.Index(fields=['post', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} liked {self.post.id}"


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'created_at']),
        ]

    def __str__(self):
        return f"Comment by {self.user.username} on post {self.post.id}"


class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following_relations')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='follower_relations')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')
        indexes = [
            models.Index(fields=['follower', 'following']),
            models.Index(fields=['following', 'follower']),
        ]

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"


class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} saved post {self.post.id}"


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('follow', 'Follow'),
        ('message', 'Message'),
    )
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='notifications', blank=True, null=True)
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['receiver', 'is_read', '-created_at']),
            models.Index(fields=['receiver', '-created_at']),
        ]

    def __str__(self):
        return f"Notification for {self.receiver.username} from {self.sender.username} ({self.notification_type})"


class Story(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stories')
    image = models.ImageField(upload_to=generate_upload_path('stories'), blank=True, null=True)
    video = models.FileField(upload_to=generate_upload_path('stories'), blank=True, null=True)
    music = models.FileField(upload_to=generate_upload_path('stories'), blank=True, null=True)
    caption = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"Story by {self.user.username} at {self.created_at}"

    @property
    def get_image_url(self):
        return get_media_url(self.image)

    @property
    def get_video_url(self):
        return get_media_url(self.video)

    @property
    def get_music_url(self):
        return get_media_url(self.music)


# =====================================================================
# DIRECT MESSAGING ARCHITECTURE (Instagram Direct)
# =====================================================================

class Conversation(models.Model):
    DIRECT = 'direct'
    GROUP = 'group'
    TYPE_CHOICES = [
        (DIRECT, 'Direct'),
        (GROUP, 'Group'),
    ]

    conversation_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=DIRECT)
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['-updated_at']),
        ]

    def __str__(self):
        return f"Conversation #{self.id} ({self.conversation_type})"

    def get_partner(self, current_user=None):
        """For direct 1-on-1 conversations, returns the other participant User."""
        if hasattr(self, 'partner') and self.partner:
            return self.partner
        if hasattr(self, '_prefetched_objects_cache') and 'participants' in self._prefetched_objects_cache:
            for p in self.participants.all():
                if current_user and p.user_id != getattr(current_user, 'id', None):
                    return p.user
                elif not current_user:
                    return p.user
            return None

        if current_user:
            participant = self.participants.exclude(user=current_user).select_related('user', 'user__profile').first()
        else:
            participant = self.participants.select_related('user', 'user__profile').first()
        return participant.user if participant else None

    def get_last_message(self):
        """Returns the latest non-deleted message."""
        if hasattr(self, 'cached_last_message'):
            return self.cached_last_message
        return self.messages.filter(is_deleted=False).select_related('sender', 'sender__profile').order_by('-created_at').first()

    def get_unread_count(self, user):
        """Calculates count of incoming unread messages for this user."""
        if hasattr(self, 'unread_count'):
            return self.unread_count
        participant = self.participants.filter(user=user).first()
        if not participant:
            return 0
        qs = self.messages.filter(is_deleted=False).exclude(sender=user)
        if participant.last_read_at:
            qs = qs.filter(created_at__gt=participant.last_read_at)
        return qs.count()


class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversation_participations')
    last_read_at = models.DateTimeField(null=True, blank=True)
    hidden_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    is_muted = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['conversation', 'user'], name='unique_participant')
        ]
        indexes = [
            models.Index(fields=['user', 'hidden_at']),
            models.Index(fields=['conversation', 'user']),
        ]

    def __str__(self):
        return f"{self.user.username} in #{self.conversation.id}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to=generate_upload_path('direct'), blank=True, null=True)
    voice_note = models.FileField(upload_to=generate_upload_path('voice_notes'), blank=True, null=True)
    post = models.ForeignKey(Post, on_delete=models.SET_NULL, null=True, blank=True, related_name='shared_in_messages')
    parent_message = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    read_at = models.DateTimeField(null=True, blank=True)
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', '-created_at']),
            models.Index(fields=['conversation', 'is_deleted', '-created_at']),
            models.Index(fields=['conversation', 'id']),
            models.Index(fields=['sender', '-created_at']),
        ]

    def __str__(self):
        return f"Message #{self.id} from {self.sender.username} in #{self.conversation.id}"

    @property
    def get_image_url(self):
        return get_media_url(self.image)

    @property
    def get_voice_note_url(self):
        return get_media_url(self.voice_note)

    @property
    def decrypted_content(self):
        from .utils.encryption import decrypt_message_text
        return decrypt_message_text(self.content)

    def can_edit(self, user=None):
        """Allows editing only by original sender within 5 minutes of creation."""
        if not user or self.sender_id != getattr(user, 'id', None) or self.is_deleted:
            return False
        from datetime import timedelta
        return timezone.now() - self.created_at <= timedelta(minutes=5)

    def can_delete(self, user=None):
        """Allows deletion/unsend by original sender at any time."""
        if not user or self.sender_id != getattr(user, 'id', None):
            return False
        return True


class MessageReaction(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_reactions')
    emoji = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user')
        indexes = [
            models.Index(fields=['message', 'user']),
        ]

    def __str__(self):
        return f"{self.user.username} reacted {self.emoji} on msg #{self.message_id}"

