from django.contrib import admin
from .models import (
    UserProfile, Post, Like, Comment, Follow, Bookmark,
    Notification, Story, Conversation, ConversationParticipant, Message
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'followers_count', 'following_count')
    search_fields = ('user__username', 'bio')

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'likes_count', 'comments_count')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'caption')

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'created_at')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'created_at')
    search_fields = ('user__username', 'content')

@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following', 'created_at')

@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'created_at')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('receiver', 'sender', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')

@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    list_filter = ('created_at',)

class ConversationParticipantInline(admin.TabularInline):
    model = ConversationParticipant
    extra = 1

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation_type', 'title', 'updated_at', 'created_at')
    list_filter = ('conversation_type', 'created_at')
    inlines = [ConversationParticipantInline]

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'content', 'created_at', 'read_at', 'is_deleted')
    list_filter = ('created_at', 'is_deleted')
    search_fields = ('content', 'sender__username')
