"""Protocol definitions for Deck-Link communication."""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
import msgpack  # type: ignore
import time
import uuid


class MessageType(str, Enum):
    """Types of messages that can be sent between clients."""

    # Connection establishment
    CONNECTION_REQUEST = "connection_request"
    CHALLENGE_RESPONSE = "challenge_response"
    AUTH_ATTEMPT = "auth_attempt"
    AUTH_RESULT = "auth_result"

    # Connection management
    PING = "ping"
    PONG = "pong"
    DISCONNECT = "disconnect"

    # Data transfer (for future use)
    FILE_TRANSFER = "file_transfer"
    KEYBOARD_INPUT = "keyboard_input"
    CONTROLLER_INPUT = "controller_input"
    AUDIO_STREAM = "audio_stream"
    NOTIFICATION = "notification"

    # Errors
    ERROR = "error"


class ConnectionState(str, Enum):
    """States of a connection."""

    DISCONNECTED = "disconnected"
    AWAITING_CHALLENGE = "awaiting_challenge"  # Initiator waiting for challenge
    CHALLENGE_SENT = "challenge_sent"  # Receiver sent challenge, waiting for auth
    AWAITING_AUTH_INPUT = "awaiting_auth_input"  # Initiator needs to enter passphrase
    CONNECTED = "connected"
    ERROR = "error"


class Message(BaseModel):
    """Base message structure for all communication."""

    type: MessageType
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = Field(default_factory=time.time)
    payload: dict[str, Any] = Field(default_factory=dict)

    def to_bytes(self) -> bytes:
        """Serialize message to msgpack bytes."""
        return msgpack.packb(self.model_dump(), use_bin_type=True)

    @classmethod
    def from_bytes(cls, data: bytes) -> "Message":
        """Deserialize message from msgpack bytes."""
        unpacked = msgpack.unpackb(data, raw=False)
        return cls(**unpacked)

    def to_json(self) -> str:
        """Serialize to JSON string (for WebSocket text frames)."""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> "Message":
        """Deserialize from JSON string."""
        return cls.model_validate_json(data)


# Convenience factory functions for common messages


def connection_request(sender_name: str, sender_ip: str, sender_port: int) -> Message:
    """Create a connection request message."""
    return Message(
        type=MessageType.CONNECTION_REQUEST,
        payload={
            "sender_name": sender_name,
            "sender_ip": sender_ip,
            "sender_port": sender_port,
        },
    )


def challenge_response(session_id: str, receiver_name: str) -> Message:
    """Create a challenge response (passphrase is displayed on UI, not sent)."""
    return Message(
        type=MessageType.CHALLENGE_RESPONSE,
        session_id=session_id,
        payload={
            "receiver_name": receiver_name,
            "message": "Enter the passphrase shown on the other device",
        },
    )


def auth_attempt(session_id: str, passphrase: str) -> Message:
    """Create an authentication attempt with the passphrase."""
    return Message(
        type=MessageType.AUTH_ATTEMPT,
        session_id=session_id,
        payload={
            "passphrase": passphrase,
        },
    )


def auth_result(session_id: str, success: bool, message: str = "") -> Message:
    """Create an authentication result message."""
    return Message(
        type=MessageType.AUTH_RESULT,
        session_id=session_id,
        payload={
            "success": success,
            "message": message,
        },
    )


def ping() -> Message:
    """Create a ping message."""
    return Message(type=MessageType.PING)


def pong(ping_session_id: str) -> Message:
    """Create a pong message in response to a ping."""
    return Message(
        type=MessageType.PONG,
        session_id=ping_session_id,
    )


def disconnect(reason: str = "User requested disconnect") -> Message:
    """Create a disconnect message."""
    return Message(type=MessageType.DISCONNECT, payload={"reason": reason})


def error(message: str, code: str = "UNKNOWN") -> Message:
    """Create an error message."""
    return Message(
        type=MessageType.ERROR,
        payload={
            "message": message,
            "code": code,
        },
    )


def notification(title: str, body: str, icon: Optional[str] = None) -> Message:
    """Create a notification message."""
    return Message(
        type=MessageType.NOTIFICATION,
        payload={
            "title": title,
            "body": body,
            "icon": icon,
        },
    )
