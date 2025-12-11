"""mDNS discovery for finding Deck-Link peers on the local network."""

import asyncio
import socket
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional
from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser, ServiceListener  # type: ignore

from . import PORT, SERVICE_TYPE, SERVICE_NAME

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredPeer:
    """A discovered Deck-Link peer on the network."""

    name: str
    host: str
    port: int
    addresses: list[str] = field(default_factory=list)
    properties: dict[str, str] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        """Human-readable name for the peer."""
        return self.properties.get("device_name", self.name)

    @property
    def device_type(self) -> str:
        """Type of device (laptop or deck)."""
        return self.properties.get("device_type", "unknown")


class PeerDiscoveryListener(ServiceListener):
    """Listener for mDNS service discovery events."""

    def __init__(
        self,
        on_peer_found: Optional[Callable[[DiscoveredPeer], None]] = None,
        on_peer_lost: Optional[Callable[[str], None]] = None,
    ):
        self.peers: dict[str, DiscoveredPeer] = {}
        self.on_peer_found = on_peer_found
        self.on_peer_lost = on_peer_lost

    def add_service(self, zc: Zeroconf, service_type: str, name: str) -> None:
        """Called when a new service is discovered."""
        info = zc.get_service_info(service_type, name)
        if info:
            self._handle_service_info(name, info)

    def update_service(self, zc: Zeroconf, service_type: str, name: str) -> None:
        """Called when a service is updated."""
        info = zc.get_service_info(service_type, name)
        if info:
            self._handle_service_info(name, info)

    def remove_service(self, zc: Zeroconf, service_type: str, name: str) -> None:
        """Called when a service is removed."""
        if name in self.peers:
            del self.peers[name]
            logger.info(f"Peer lost: {name}")
            if self.on_peer_lost:
                self.on_peer_lost(name)

    def _handle_service_info(self, name: str, info: ServiceInfo) -> None:
        """Process discovered service info."""
        addresses = []
        for addr in info.addresses:
            try:
                addresses.append(socket.inet_ntoa(addr))
            except Exception:
                pass

        properties = {}
        for k, v in info.properties.items():
            key = k.decode() if isinstance(k, bytes) else str(k)
            val = v.decode() if isinstance(v, bytes) else str(v)
            properties[key] = val

        peer = DiscoveredPeer(
            name=name,
            host=info.server or (addresses[0] if addresses else ""),
            port=info.port,
            addresses=addresses,
            properties=properties,
        )

        self.peers[name] = peer
        logger.info(f"Peer found: {peer.display_name} at {peer.host}:{peer.port}")

        if self.on_peer_found:
            self.on_peer_found(peer)


class Discovery:
    """
    Manages mDNS service advertisement and discovery.

    Uses synchronous zeroconf to avoid async compatibility issues.
    """

    def __init__(
        self,
        device_name: str,
        device_type: str = "laptop",
        port: int = PORT,
        on_peer_found: Optional[Callable[[DiscoveredPeer], None]] = None,
        on_peer_lost: Optional[Callable[[str], None]] = None,
    ):
        self.device_name = device_name
        self.device_type = device_type
        self.port = port
        self.on_peer_found = on_peer_found
        self.on_peer_lost = on_peer_lost

        self._zeroconf: Optional[Zeroconf] = None
        self._browser: Optional[ServiceBrowser] = None
        self._service_info: Optional[ServiceInfo] = None
        self._listener: Optional[PeerDiscoveryListener] = None
        self._running = False

    def _get_local_ip(self) -> str:
        """Get the local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    async def start(self) -> None:
        """Start advertising this service and browsing for peers."""
        if self._running:
            return

        # Run zeroconf setup in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._start_sync)

    def _start_sync(self) -> None:
        """Synchronous startup of zeroconf."""
        self._zeroconf = Zeroconf()

        # Create service info for advertising
        local_ip = self._get_local_ip()
        service_name = f"{self.device_name}.{SERVICE_TYPE}"

        self._service_info = ServiceInfo(
            SERVICE_TYPE,
            service_name,
            addresses=[socket.inet_aton(local_ip)],
            port=self.port,
            properties={
                "device_name": self.device_name,
                "device_type": self.device_type,
                "version": "0.1.0",
            },
        )

        # Register our service
        self._zeroconf.register_service(self._service_info)
        logger.info(f"Advertising as {service_name} on {local_ip}:{self.port}")

        # Set up listener for peer discovery
        self._listener = PeerDiscoveryListener(
            on_peer_found=self._on_peer_found,
            on_peer_lost=self.on_peer_lost,
        )

        # Start browsing for peers
        self._browser = ServiceBrowser(
            self._zeroconf,
            SERVICE_TYPE,
            self._listener,
        )

        self._running = True
        logger.info("Discovery started")

    def _on_peer_found(self, peer: DiscoveredPeer) -> None:
        """Filter out self from discovered peers."""
        if peer.name.startswith(self.device_name):
            return
        if self.on_peer_found:
            self.on_peer_found(peer)

    async def stop(self) -> None:
        """Stop advertising and browsing."""
        if not self._running:
            return

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._stop_sync)

    def _stop_sync(self) -> None:
        """Synchronous shutdown of zeroconf."""
        if self._browser:
            self._browser.cancel()
            self._browser = None

        if self._service_info and self._zeroconf:
            self._zeroconf.unregister_service(self._service_info)
            self._service_info = None

        if self._zeroconf:
            self._zeroconf.close()
            self._zeroconf = None

        self._running = False
        logger.info("Discovery stopped")

    def get_peers(self) -> list[DiscoveredPeer]:
        """Get list of currently discovered peers."""
        if not self._listener:
            return []

        return [
            peer
            for peer in self._listener.peers.values()
            if not peer.name.startswith(self.device_name)
        ]

    def get_local_info(self) -> dict:
        """Get local service info for display."""
        return {
            "name": self.device_name,
            "type": self.device_type,
            "ip": self._get_local_ip(),
            "port": self.port,
        }


async def discover_peers_once(timeout: float = 3.0) -> list[DiscoveredPeer]:
    """Quick one-shot discovery of peers."""
    peers: list[DiscoveredPeer] = []

    def on_found(peer: DiscoveredPeer) -> None:
        peers.append(peer)

    discovery = Discovery(
        device_name=f"scanner-{socket.gethostname()}",
        on_peer_found=on_found,
    )

    await discovery.start()
    await asyncio.sleep(timeout)
    await discovery.stop()

    return peers


if __name__ == "__main__":

    async def main() -> None:
        logging.basicConfig(level=logging.INFO)
        print("Scanning for Deck-Link peers...")
        peers = await discover_peers_once(timeout=5.0)

        if peers:
            print(f"\nFound {len(peers)} peer(s):")
            for peer in peers:
                print(
                    f"  - {peer.display_name} ({peer.device_type}) at {peer.host}:{peer.port}"
                )
        else:
            print("No peers found.")

    asyncio.run(main())
