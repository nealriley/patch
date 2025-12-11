"""WebSocket server for Deck-Link communication."""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from websockets.server import serve, WebSocketServerProtocol  # type: ignore
from websockets.client import connect, WebSocketClientProtocol  # type: ignore
from websockets.exceptions import ConnectionClosed  # type: ignore

from . import PORT
from .protocol import (
    Message,
    MessageType,
    ConnectionState,
    connection_request,
    challenge_response,
    auth_attempt,
    auth_result,
    ping,
    pong,
    disconnect,
    error,
)
from .passphrase import generate_passphrase, validate_passphrase

logger = logging.getLogger(__name__)


@dataclass
class PeerInfo:
    """Information about a connected peer."""

    name: str
    ip: str
    port: int
    websocket: Optional[WebSocketServerProtocol | WebSocketClientProtocol] = None


@dataclass
class ConnectionSession:
    """Tracks an active connection session during authentication."""

    session_id: str
    passphrase: str
    peer_info: Optional[PeerInfo] = None
    state: ConnectionState = ConnectionState.DISCONNECTED


EventCallback = Callable[[str, dict[str, Any]], None]


class DeckLinkServer:
    """
    Main server class for Deck-Link.

    Handles both incoming connections (as server) and outgoing connections (as client).
    Provides event callbacks for UI integration.
    """

    def __init__(
        self,
        device_name: str,
        device_type: str = "laptop",
        port: int = PORT,
        on_event: Optional[EventCallback] = None,
    ):
        self.device_name = device_name
        self.device_type = device_type
        self.port = port
        self.on_event = on_event

        # Connection state
        self._state = ConnectionState.DISCONNECTED
        self._current_session: Optional[ConnectionSession] = None
        self._peer: Optional[PeerInfo] = None
        self._websocket: Optional[WebSocketServerProtocol | WebSocketClientProtocol] = (
            None
        )

        # Server
        self._server: Optional[asyncio.Server] = None
        self._running = False

        # Ping/pong
        self._ping_task: Optional[asyncio.Task[None]] = None
        self._last_pong: float = 0

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED

    @property
    def peer(self) -> Optional[PeerInfo]:
        return self._peer

    def _emit(self, event: str, data: dict[str, Any]) -> None:
        """Emit an event to the UI."""
        logger.debug(f"Event: {event} - {data}")
        if self.on_event:
            self.on_event(event, data)

    def _set_state(self, state: ConnectionState) -> None:
        """Update connection state and notify UI."""
        old_state = self._state
        self._state = state
        self._emit(
            "state_changed",
            {
                "old_state": old_state.value,
                "new_state": state.value,
            },
        )

    async def start(self) -> None:
        """Start the WebSocket server."""
        if self._running:
            return

        self._server = await serve(
            self._handle_connection,
            "0.0.0.0",
            self.port,
        )
        self._running = True
        logger.info(f"Server started on port {self.port}")
        self._emit("server_started", {"port": self.port})

    async def stop(self) -> None:
        """Stop the server and disconnect."""
        if self._ping_task:
            self._ping_task.cancel()
            self._ping_task = None

        if self._websocket:
            await self._websocket.close()
            self._websocket = None

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        self._running = False
        self._set_state(ConnectionState.DISCONNECTED)
        self._peer = None
        self._current_session = None
        logger.info("Server stopped")
        self._emit("server_stopped", {})

    async def _handle_connection(self, websocket: WebSocketServerProtocol) -> None:
        """Handle an incoming WebSocket connection."""
        remote_addr = websocket.remote_address
        logger.info(f"Incoming connection from {remote_addr}")

        try:
            async for raw_message in websocket:
                if isinstance(raw_message, bytes):
                    message = Message.from_bytes(raw_message)
                else:
                    message = Message.from_json(raw_message)

                await self._handle_message(message, websocket, is_server=True)
        except ConnectionClosed:
            logger.info(f"Connection closed from {remote_addr}")
            if self._websocket == websocket:
                self._handle_disconnect()
        except Exception as e:
            logger.error(f"Error handling connection: {e}")
            self._handle_disconnect()

    async def _handle_message(
        self,
        message: Message,
        websocket: WebSocketServerProtocol | WebSocketClientProtocol,
        is_server: bool,
    ) -> None:
        """Process an incoming message based on type and current state."""
        logger.debug(f"Received: {message.type.value}")

        if message.type == MessageType.CONNECTION_REQUEST:
            await self._handle_connection_request(message, websocket)

        elif message.type == MessageType.CHALLENGE_RESPONSE:
            await self._handle_challenge_response(message)

        elif message.type == MessageType.AUTH_ATTEMPT:
            await self._handle_auth_attempt(message, websocket)

        elif message.type == MessageType.AUTH_RESULT:
            await self._handle_auth_result(message, websocket)

        elif message.type == MessageType.PING:
            await self._handle_ping(message, websocket)

        elif message.type == MessageType.PONG:
            self._handle_pong(message)

        elif message.type == MessageType.DISCONNECT:
            self._handle_disconnect()

        elif message.type == MessageType.NOTIFICATION:
            self._emit("notification", message.payload)

        else:
            logger.warning(f"Unhandled message type: {message.type}")

    async def _handle_connection_request(
        self,
        message: Message,
        websocket: WebSocketServerProtocol,
    ) -> None:
        """Handle incoming connection request - generate challenge."""
        if self._state == ConnectionState.CONNECTED:
            # Already connected, reject
            err = error("Already connected to another peer", "ALREADY_CONNECTED")
            await websocket.send(err.to_json())
            return

        # Generate passphrase for challenge
        passphrase = generate_passphrase()

        self._current_session = ConnectionSession(
            session_id=message.session_id,
            passphrase=passphrase,
            peer_info=PeerInfo(
                name=message.payload.get("sender_name", "Unknown"),
                ip=message.payload.get("sender_ip", ""),
                port=message.payload.get("sender_port", PORT),
                websocket=websocket,
            ),
        )

        self._set_state(ConnectionState.CHALLENGE_SENT)

        # Notify UI to display passphrase
        self._emit(
            "challenge_generated",
            {
                "session_id": message.session_id,
                "passphrase": passphrase,
                "peer_name": message.payload.get("sender_name", "Unknown"),
            },
        )

        # Send challenge response (without passphrase - that's shown on screen)
        response = challenge_response(message.session_id, self.device_name)
        await websocket.send(response.to_json())

    async def _handle_challenge_response(self, message: Message) -> None:
        """Handle challenge response - prompt user for passphrase input."""
        if self._state != ConnectionState.AWAITING_CHALLENGE:
            logger.warning("Unexpected challenge response")
            return

        self._set_state(ConnectionState.AWAITING_AUTH_INPUT)

        # Notify UI to show passphrase input
        self._emit(
            "passphrase_required",
            {
                "session_id": message.session_id,
                "peer_name": message.payload.get("receiver_name", "Unknown"),
            },
        )

    async def _handle_auth_attempt(
        self,
        message: Message,
        websocket: WebSocketServerProtocol,
    ) -> None:
        """Handle authentication attempt - verify passphrase."""
        if not self._current_session:
            err = error("No active session", "NO_SESSION")
            await websocket.send(err.to_json())
            return

        if message.session_id != self._current_session.session_id:
            err = error("Invalid session", "INVALID_SESSION")
            await websocket.send(err.to_json())
            return

        input_passphrase = message.payload.get("passphrase", "")

        if validate_passphrase(input_passphrase, self._current_session.passphrase):
            # Success!
            self._websocket = websocket
            self._peer = self._current_session.peer_info
            self._set_state(ConnectionState.CONNECTED)

            result = auth_result(message.session_id, True, "Connected!")
            await websocket.send(result.to_json())

            self._emit(
                "connected",
                {
                    "peer_name": self._peer.name if self._peer else "Unknown",
                    "peer_ip": self._peer.ip if self._peer else "",
                },
            )

            # Start ping loop
            self._start_ping_loop()
        else:
            # Failed
            result = auth_result(message.session_id, False, "Incorrect passphrase")
            await websocket.send(result.to_json())

            self._emit(
                "auth_failed",
                {
                    "reason": "Incorrect passphrase",
                },
            )

            # Reset state
            self._set_state(ConnectionState.DISCONNECTED)
            self._current_session = None

    async def _handle_auth_result(
        self,
        message: Message,
        websocket: WebSocketClientProtocol,
    ) -> None:
        """Handle authentication result from server."""
        success = message.payload.get("success", False)

        if success:
            self._websocket = websocket
            self._set_state(ConnectionState.CONNECTED)

            self._emit(
                "connected",
                {
                    "peer_name": self._peer.name if self._peer else "Unknown",
                    "peer_ip": self._peer.ip if self._peer else "",
                },
            )

            # Start ping loop
            self._start_ping_loop()
        else:
            self._set_state(ConnectionState.ERROR)
            self._emit(
                "auth_failed",
                {
                    "reason": message.payload.get("message", "Authentication failed"),
                },
            )

    async def _handle_ping(
        self,
        message: Message,
        websocket: WebSocketServerProtocol | WebSocketClientProtocol,
    ) -> None:
        """Respond to ping with pong."""
        response = pong(message.session_id)
        await websocket.send(response.to_json())

    def _handle_pong(self, message: Message) -> None:
        """Record pong received."""
        import time

        self._last_pong = time.time()

    def _handle_disconnect(self) -> None:
        """Handle disconnection."""
        self._set_state(ConnectionState.DISCONNECTED)
        self._websocket = None
        self._peer = None
        self._current_session = None

        if self._ping_task:
            self._ping_task.cancel()
            self._ping_task = None

        self._emit("disconnected", {})

    def _start_ping_loop(self) -> None:
        """Start the ping/pong heartbeat loop."""

        async def ping_loop() -> None:
            import time

            while self._state == ConnectionState.CONNECTED and self._websocket:
                try:
                    self._last_pong = time.time()
                    await self._websocket.send(ping().to_json())
                    await asyncio.sleep(5)

                    # Check if pong was received
                    if time.time() - self._last_pong > 10:
                        logger.warning("Ping timeout - disconnecting")
                        self._handle_disconnect()
                        break
                except Exception as e:
                    logger.error(f"Ping error: {e}")
                    self._handle_disconnect()
                    break

        self._ping_task = asyncio.create_task(ping_loop())

    # Client-side methods (for initiating connections)

    async def connect_to(self, host: str, port: int = PORT) -> None:
        """Initiate a connection to another Deck-Link instance."""
        if self._state != ConnectionState.DISCONNECTED:
            logger.warning("Already connected or connecting")
            return

        self._set_state(ConnectionState.AWAITING_CHALLENGE)

        try:
            uri = f"ws://{host}:{port}"
            websocket = await connect(uri)

            self._peer = PeerInfo(name="", ip=host, port=port, websocket=websocket)

            # Send connection request
            request = connection_request(
                sender_name=self.device_name,
                sender_ip="",  # Will be determined by receiver
                sender_port=self.port,
            )
            await websocket.send(request.to_json())

            # Store session info
            self._current_session = ConnectionSession(
                session_id=request.session_id,
                passphrase="",  # We don't know it yet
                peer_info=self._peer,
            )

            # Start listening for responses
            asyncio.create_task(self._client_listen(websocket))

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._set_state(ConnectionState.ERROR)
            self._emit("connection_error", {"error": str(e)})

    async def _client_listen(self, websocket: WebSocketClientProtocol) -> None:
        """Listen for messages as a client."""
        try:
            async for raw_message in websocket:
                if isinstance(raw_message, bytes):
                    message = Message.from_bytes(raw_message)
                else:
                    message = Message.from_json(raw_message)

                await self._handle_message(message, websocket, is_server=False)
        except ConnectionClosed:
            logger.info("Client connection closed")
            self._handle_disconnect()
        except Exception as e:
            logger.error(f"Client error: {e}")
            self._handle_disconnect()

    async def submit_passphrase(self, passphrase: str) -> None:
        """Submit passphrase (called from UI after user enters it)."""
        if self._state != ConnectionState.AWAITING_AUTH_INPUT:
            logger.warning("Not awaiting passphrase input")
            return

        if not self._current_session or not self._peer or not self._peer.websocket:
            logger.error("No active session")
            return

        attempt = auth_attempt(self._current_session.session_id, passphrase)
        await self._peer.websocket.send(attempt.to_json())

    async def disconnect_peer(self) -> None:
        """Disconnect from current peer."""
        if self._websocket:
            try:
                await self._websocket.send(disconnect().to_json())
                await self._websocket.close()
            except Exception:
                pass

        self._handle_disconnect()

    async def send_notification(self, title: str, body: str) -> None:
        """Send a notification to the connected peer."""
        if not self.is_connected or not self._websocket:
            logger.warning("Not connected")
            return

        from .protocol import notification

        msg = notification(title, body)
        await self._websocket.send(msg.to_json())

    def get_status(self) -> dict[str, Any]:
        """Get current status for UI."""
        return {
            "state": self._state.value,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "port": self.port,
            "peer": {
                "name": self._peer.name,
                "ip": self._peer.ip,
                "port": self._peer.port,
            }
            if self._peer
            else None,
            "session_id": self._current_session.session_id
            if self._current_session
            else None,
        }
