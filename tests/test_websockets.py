import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser
from core.consumers import ChatConsumer
from core.models import Message

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_websocket_unauthenticated_rejected(conversation_ab):
    comm = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{conversation_ab.id}/")
    comm.scope["url_route"] = {"kwargs": {"conversation_id": str(conversation_ab.id)}}
    comm.scope["user"] = AnonymousUser()

    connected, close_code = await comm.connect()
    assert not connected
    assert close_code == 4401
    await comm.disconnect()

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_websocket_missing_conversation_rejected(user_a):
    comm = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
    comm.scope["url_route"] = {"kwargs": {}}
    comm.scope["user"] = user_a

    connected, close_code = await comm.connect()
    assert not connected
    assert close_code == 4400
    await comm.disconnect()

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_websocket_non_participant_rejected(conversation_ab, user_c):
    comm = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{conversation_ab.id}/")
    comm.scope["url_route"] = {"kwargs": {"conversation_id": str(conversation_ab.id)}}
    comm.scope["user"] = user_c

    connected, close_code = await comm.connect()
    assert not connected
    assert close_code == 4403
    await comm.disconnect()

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_websocket_participant_connect_success(conversation_ab, user_a):
    comm = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{conversation_ab.id}/")
    comm.scope["url_route"] = {"kwargs": {"conversation_id": str(conversation_ab.id)}}
    comm.scope["user"] = user_a

    connected, _ = await comm.connect()
    assert connected is True

    init_msg = await comm.receive_json_from()
    assert init_msg["type"] == "connection_established"
    assert init_msg["conversation_id"] == str(conversation_ab.id)
    assert init_msg["username"] == user_a.username

    await comm.disconnect()

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_websocket_ping_pong(conversation_ab, user_a):
    comm = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{conversation_ab.id}/")
    comm.scope["url_route"] = {"kwargs": {"conversation_id": str(conversation_ab.id)}}
    comm.scope["user"] = user_a

    connected, _ = await comm.connect()
    assert connected is True
    # Consume init message
    await comm.receive_json_from()

    # Send heartbeat ping
    await comm.send_json_to({"action": "ping"})
    pong = await comm.receive_json_from()
    assert pong["type"] == "pong"

    await comm.disconnect()

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_websocket_reconnect_sync(conversation_ab, user_a):
    comm = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{conversation_ab.id}/")
    comm.scope["url_route"] = {"kwargs": {"conversation_id": str(conversation_ab.id)}}
    comm.scope["user"] = user_a

    connected, _ = await comm.connect()
    assert connected is True
    await comm.receive_json_from()

    await comm.send_json_to({"action": "sync", "last_message_id": 0})
    sync_resp = await comm.receive_json_from()
    assert sync_resp["type"] == "sync_history"
    assert sync_resp["conversation_id"] == str(conversation_ab.id)
    assert isinstance(sync_resp["messages"], list)

    await comm.disconnect()

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_websocket_send_and_receive_message(conversation_ab, user_a):
    comm = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{conversation_ab.id}/")
    comm.scope["url_route"] = {"kwargs": {"conversation_id": str(conversation_ab.id)}}
    comm.scope["user"] = user_a

    connected, _ = await comm.connect()
    assert connected is True
    await comm.receive_json_from()

    await comm.send_json_to({
        "action": "send_message",
        "content": "Hello via real-time WebSocket!"
    })

    msg_resp = await comm.receive_json_from()
    assert msg_resp["type"] == "new_message"
    assert msg_resp["message"]["content"] == "Hello via real-time WebSocket!"
    assert msg_resp["message"]["sender"]["username"] == user_a.username

    await comm.disconnect()

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_websocket_disconnect_cleanup(conversation_ab, user_a):
    comm = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{conversation_ab.id}/")
    comm.scope["url_route"] = {"kwargs": {"conversation_id": str(conversation_ab.id)}}
    comm.scope["user"] = user_a

    connected, _ = await comm.connect()
    assert connected is True
    await comm.receive_json_from()

    await comm.disconnect()
    # Ensure communicator closed cleanly with no remaining messages
    assert await comm.receive_nothing()
