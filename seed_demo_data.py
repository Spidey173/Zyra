"""
Database utility script for Zyra.
Usage:
  python seed_demo_data.py --clear      # Clears all user data, posts, conversations, stories
  python seed_demo_data.py              # Seeds tester 'ash' and superuser 'Spidey' with sample chat
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction
from django.contrib.auth.models import User
from core.models import UserProfile, Post, Comment, Like, Follow, Bookmark, Notification, Story, Conversation, ConversationParticipant, Message
from core.services.messaging import get_or_create_direct_conversation, send_message

def clear_database():
    print("Purging database records...")
    with transaction.atomic():
        Message.objects.all().delete()
        ConversationParticipant.objects.all().delete()
        Conversation.objects.all().delete()
        Notification.objects.all().delete()
        Bookmark.objects.all().delete()
        Like.objects.all().delete()
        Comment.objects.all().delete()
        Follow.objects.all().delete()
        Story.objects.all().delete()
        Post.objects.all().delete()
        UserProfile.objects.all().delete()
        User.objects.all().delete()
    print("✓ All data successfully cleared.")

def seed_test_accounts():
    print("Creating Spidey (Superuser) and ash (Tester) accounts...")
    
    with transaction.atomic():
        # Create Superuser Spidey
        spidey = User.objects.create_superuser(
            username="Spidey",
            email="spidey@zyra.app",
            first_name="Spidey",
            last_name="Admin"
        )
        spidey.set_password("Spidey@173")
        spidey.save()
        spidey.profile.bio = "Zyra Creator & Administrator 🕸️"
        spidey.profile.save()

        # Create Tester ash
        ash = User.objects.create_user(
            username="ash",
            email="ash@zyra.app",
            first_name="Ash",
            last_name="Tester"
        )
        ash.set_password("Password123!")
        ash.save()
        ash.profile.bio = "Zyra QA Tester 🚀"
        ash.profile.save()

        # Mutual follow
        Follow.objects.create(follower=spidey, following=ash)
        Follow.objects.create(follower=ash, following=spidey)

        # Create sample post by Spidey
        post = Post.objects.create(
            user=spidey,
            caption="Welcome to Zyra! The real-time messaging, stories, and reels are officially live. ✨ #launch"
        )

        # Create sample conversations and messages between Spidey and ash
        conv, _ = get_or_create_direct_conversation(ash, spidey)
        send_message(sender=spidey, conversation_id=conv.id, content="Hi Ash, welcome to Zyra Direct Messaging! Let me know if everything is running perfectly.")
        send_message(sender=ash, conversation_id=conv.id, content="Thanks Spidey! The real-time messaging, unread counts, and optimistic bubble loading are working super smooth! 🔥")

    print("✓ Seeding successfully completed!")
    print("  Superuser : Spidey / Spidey@173")
    print("  Tester    : ash / Password123!")

if __name__ == '__main__':
    if '--clear' in sys.argv:
        clear_database()
    else:
        clear_database()
        seed_test_accounts()
