"""Main entry point for Deck-Link CLI and IPC server."""

import asyncio
import json
import logging
import socket
import sys
from typing import Any, Optional

import click

from . import PORT
from .server import DeckLinkServer
from .discovery import Discovery, DiscoveredPeer

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class JsonRpcServer:
    """
    JSON-RPC server over stdin/stdout for Tauri IPC.

    Tauri sidecar communicates with the Python process via JSON messages
    over stdin/stdout.
    """

    def __init__(self, deck_link: DeckLinkServer, discovery: Discovery):
        self.deck_link = deck_link
        self.discovery = discovery
        self._running = False

    async def start(self) -> None:
        """Start listening for commands on stdin."""
        self._running = True

        # Make stdin non-blocking
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while self._running:
            try:
                line = await reader.readline()
                if not line:
                    break

                command = json.loads(line.decode().strip())
                response = await self._handle_command(command)
                self._send_response(response)

            except json.JSONDecodeError as e:
                self._send_response({"error": f"Invalid JSON: {e}"})
            except Exception as e:
                logger.error(f"Command error: {e}")
                self._send_response({"error": str(e)})

    async def _handle_command(self, command: dict[str, Any]) -> dict[str, Any]:
        """Handle a JSON-RPC command."""
        method = command.get("method", "")
        params = command.get("params", {})
        request_id = command.get("id")

        result: Any = None

        if method == "get_status":
            result = self.deck_link.get_status()
            result["local_info"] = self.discovery.get_local_info()

        elif method == "get_peers":
            peers = self.discovery.get_peers()
            result = [
                {
                    "name": p.display_name,
                    "host": p.host,
                    "port": p.port,
                    "device_type": p.device_type,
                }
                for p in peers
            ]

        elif method == "connect":
            host = params.get("host", "")
            port = params.get("port", PORT)
            await self.deck_link.connect_to(host, port)
            result = {"status": "connecting"}

        elif method == "submit_passphrase":
            passphrase = params.get("passphrase", "")
            await self.deck_link.submit_passphrase(passphrase)
            result = {"status": "submitted"}

        elif method == "disconnect":
            await self.deck_link.disconnect_peer()
            result = {"status": "disconnected"}

        elif method == "send_notification":
            title = params.get("title", "")
            body = params.get("body", "")
            await self.deck_link.send_notification(title, body)
            result = {"status": "sent"}

        elif method == "ping":
            result = {"pong": True}

        else:
            return {"error": f"Unknown method: {method}", "id": request_id}

        return {"result": result, "id": request_id}

    def _send_response(self, response: dict[str, Any]) -> None:
        """Send a JSON response to stdout."""
        print(json.dumps(response), flush=True)

    def send_event(self, event: str, data: dict[str, Any]) -> None:
        """Send an event notification to Tauri."""
        self._send_response(
            {
                "event": event,
                "data": data,
            }
        )


def get_device_name() -> str:
    """Get a reasonable device name."""
    hostname = socket.gethostname()
    return hostname


def create_event_handler(rpc_server: Optional[JsonRpcServer]) -> Any:
    """Create an event handler that forwards to JSON-RPC."""

    def handler(event: str, data: dict[str, Any]) -> None:
        if rpc_server:
            rpc_server.send_event(event, data)
        else:
            logger.info(f"Event: {event} - {data}")

    return handler


@click.group()
def cli() -> None:
    """Deck-Link: Bridge your Steam Deck and laptop."""
    pass


@cli.command()
@click.option("--mode", type=click.Choice(["laptop", "deck"]), default="laptop")
@click.option("--name", default=None, help="Device name")
@click.option("--port", default=PORT, help="Port to listen on")
@click.option("--ipc", is_flag=True, help="Run in IPC mode for Tauri")
def run(mode: str, name: Optional[str], port: int, ipc: bool) -> None:
    """Run the Deck-Link server."""
    device_name = name or get_device_name()

    async def main() -> None:
        rpc_server: Optional[JsonRpcServer] = None

        # Create server
        server = DeckLinkServer(
            device_name=device_name,
            device_type=mode,
            port=port,
            on_event=create_event_handler(rpc_server),
        )

        # Create discovery
        discovery = Discovery(
            device_name=device_name,
            device_type=mode,
            port=port,
            on_peer_found=lambda p: logger.info(f"Peer found: {p.display_name}"),
            on_peer_lost=lambda n: logger.info(f"Peer lost: {n}"),
        )

        # Start services
        await server.start()
        await discovery.start()

        if ipc:
            # IPC mode for Tauri
            rpc_server = JsonRpcServer(server, discovery)
            # Update event handler
            server.on_event = create_event_handler(rpc_server)
            await rpc_server.start()
        else:
            # CLI mode - just keep running
            logger.info(f"Deck-Link running as {mode} '{device_name}' on port {port}")
            logger.info("Press Ctrl+C to stop")

            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                pass

        # Cleanup
        await discovery.stop()
        await server.stop()

    asyncio.run(main())


@cli.command()
@click.option("--timeout", default=5.0, help="Discovery timeout in seconds")
def scan(timeout: float) -> None:
    """Scan for Deck-Link peers on the network."""
    from .discovery import discover_peers_once

    async def main() -> None:
        click.echo(f"Scanning for {timeout} seconds...")
        peers = await discover_peers_once(timeout)

        if peers:
            click.echo(f"\nFound {len(peers)} peer(s):")
            for peer in peers:
                click.echo(f"  {peer.display_name} ({peer.device_type})")
                click.echo(f"    Address: {peer.host}:{peer.port}")
        else:
            click.echo("No peers found.")

    asyncio.run(main())


@cli.command()
@click.argument("host")
@click.option("--port", default=PORT, help="Port to connect to")
def connect(host: str, port: int) -> None:
    """Connect to a Deck-Link peer (interactive CLI)."""
    device_name = get_device_name()

    async def main() -> None:
        passphrase_entered = asyncio.Event()
        passphrase_value = ""

        def on_event(event: str, data: dict[str, Any]) -> None:
            nonlocal passphrase_value

            if event == "passphrase_required":
                click.echo(f"\nConnection accepted by {data.get('peer_name', 'peer')}")
                click.echo("Enter the passphrase shown on the other device:")
                passphrase_value = click.prompt("Passphrase", hide_input=False)
                passphrase_entered.set()

            elif event == "connected":
                click.echo(f"\nConnected to {data.get('peer_name', 'peer')}!")

            elif event == "auth_failed":
                click.echo(f"\nAuthentication failed: {data.get('reason', 'Unknown')}")

            elif event == "disconnected":
                click.echo("\nDisconnected")

            else:
                logger.debug(f"Event: {event} - {data}")

        server = DeckLinkServer(
            device_name=device_name,
            device_type="laptop",
            on_event=on_event,
        )

        await server.start()

        click.echo(f"Connecting to {host}:{port}...")
        await server.connect_to(host, port)

        # Wait for passphrase prompt
        try:
            await asyncio.wait_for(passphrase_entered.wait(), timeout=30)
            await server.submit_passphrase(passphrase_value)

            # Keep running until disconnect
            while server.is_connected:
                await asyncio.sleep(1)
        except asyncio.TimeoutError:
            click.echo("Connection timeout")
        except KeyboardInterrupt:
            pass

        await server.stop()

    asyncio.run(main())


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
