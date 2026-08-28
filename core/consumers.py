import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.exceptions import ValidationError, PermissionDenied
from .models import Conversation, Message
from .services.messaging import (
    send_message,
    edit_message,
    unsend_message,
    toggle_reaction,
    mark_conversation_read
)
from .serializers import serialize_message

class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.room_group_name = f"chat_{self.conversation_id}"

        # Reject unauthenticated users
        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        # Verify user is a participant of this conversation
        is_participant = await self.check_participant()
        if not is_participant:
            await self.close(code=4003)
            return

        # Join conversation room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Mark conversation as read on connection
        await self.mark_read_in_db()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "messages_read",
                "reader_username": self.user.username,
                "conversation_id": self.conversation_id
            }
        )

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive_json(self, content):
        action = content.get("action")

        if action == "send_message":
            text = content.get("content", "").strip()
            reply_to_id = content.get("reply_to_id")
            post_id = content.get("post_id")
            if not text and not post_id:
                return

            try:
                msg_dto = await self.create_message(text, reply_to_id, post_id)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_message",
                        "message": msg_dto
                    }
                )
            except Exception as e:
                await self.send_json({"type": "error", "message": str(e)})

        elif action == "edit_message":
            msg_id = content.get("message_id")
            new_text = content.get("content", "").strip()
            if not msg_id or not new_text:
                return

            try:
                msg_dto = await self.edit_message_in_db(msg_id, new_text)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "message_edited",
                        "message": msg_dto
                    }
                )
            except Exception as e:
                await self.send_json({"type": "error", "message": str(e)})

        elif action == "unsend_message":
            msg_id = content.get("message_id")
            if not msg_id:
                return

            try:
                await self.unsend_message_in_db(msg_id)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "message_deleted",
                        "message_id": msg_id
                    }
                )
            except Exception as e:
                await self.send_json({"type": "error", "message": str(e)})

        elif action == "react_message":
            msg_id = content.get("message_id")
            emoji = content.get("emoji", "").strip()
            if not msg_id or not emoji:
                return

            try:
                msg_dto = await self.react_message_in_db(msg_id, emoji)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "message_reaction",
                        "message": msg_dto
                    }
                )
            except Exception as e:
                await self.send_json({"type": "error", "message": str(e)})

        elif action == "typing":
            is_typing = content.get("is_typing", False)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "user_typing",
                    "sender_username": self.user.username,
                    "is_typing": is_typing
                }
            )

        elif action == "mark_read":
            await self.mark_read_in_db()
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "messages_read",
                    "reader_username": self.user.username,
                    "conversation_id": self.conversation_id
                }
            )

    # -------------------------------------------------------------------------
    # Handlers for Group Events (Pushed to WebSocket clients)
    # -------------------------------------------------------------------------
    async def chat_message(self, event):
        msg = event["message"]
        # Customize is_mine for the specific recipient
        msg_copy = dict(msg)
        msg_copy["is_mine"] = (msg["sender_id"] == self.user.id)
        msg_copy["can_edit"] = (msg["sender_id"] == self.user.id) and msg.get("can_edit", False)
        msg_copy["can_delete"] = (msg["sender_id"] == self.user.id)
        await self.send_json({
            "type": "new_message",
            "message": msg_copy
        })

    async def message_edited(self, event):
        msg = event["message"]
        msg_copy = dict(msg)
        msg_copy["is_mine"] = (msg["sender_id"] == self.user.id)
        msg_copy["can_edit"] = (msg["sender_id"] == self.user.id) and msg.get("can_edit", False)
        msg_copy["can_delete"] = (msg["sender_id"] == self.user.id)
        await self.send_json({
            "type": "message_edited",
            "message": msg_copy
        })

    async def message_deleted(self, event):
        await self.send_json({
            "type": "message_deleted",
            "message_id": event["message_id"]
        })

    async def message_reaction(self, event):
        msg = event["message"]
        msg_copy = dict(msg)
        msg_copy["is_mine"] = (msg["sender_id"] == self.user.id)
        await self.send_json({
            "type": "message_reaction",
            "message": msg_copy
        })

    async def user_typing(self, event):
        # Don't echo typing event back to the sender
        if event["sender_username"] != self.user.username:
            await self.send_json({
                "type": "user_typing",
                "sender_username": event["sender_username"],
                "is_typing": event["is_typing"]
            })

    async def messages_read(self, event):
        if event["reader_username"] != self.user.username:
            await self.send_json({
                "type": "messages_read",
                "reader_username": event["reader_username"]
            })

    # -------------------------------------------------------------------------
    # Database Sync-to-Async Helpers
    # -------------------------------------------------------------------------
    @database_sync_to_async
    def check_participant(self):
        try:
            conv = Conversation.objects.get(id=self.conversation_id)
            return conv.participants.filter(user=self.user).exists()
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def create_message(self, content, reply_to_id, post_id):
        msg = send_message(
            sender=self.user,
            conversation_id=self.conversation_id,
            content=content,
            reply_to_id=reply_to_id,
            post_id=post_id
        )
        return serialize_message(msg, self.user)

    @database_sync_to_async
    def edit_message_in_db(self, msg_id, new_content):
        msg = edit_message(msg_id, self.user, new_content)
        return serialize_message(msg, self.user)

    @database_sync_to_async
    def unsend_message_in_db(self, msg_id):
        return unsend_message(msg_id, self.user)

    @database_sync_to_async
    def react_message_in_db(self, msg_id, emoji):
        msg = toggle_reaction(msg_id, self.user, emoji)
        return serialize_message(msg, self.user)

    @database_sync_to_async
    def mark_read_in_db(self):
        try:
            conv = Conversation.objects.get(id=self.conversation_id)
            return mark_conversation_read(conv, self.user)
        except Conversation.DoesNotExist:
            return 0
