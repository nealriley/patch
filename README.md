# Deck Link

A bidirectional communication bridge between Steam Deck and Linux laptop.

## Features

- **Automatic Discovery**: Find devices on your local network via mDNS
- **Secure Pairing**: Visual passphrase verification ensures you connect to the right device
- **Touch-Friendly UI**: Designed for both desktop and Steam Deck's touchscreen
- **Bidirectional**: Both devices can send and receive data

## Quick Start

### Install Python Backend

```bash
cd deck-link
pip install -e .
```

### Run CLI (for testing)

```bash
# On laptop
deck-link run --mode laptop

# On Steam Deck
deck-link run --mode deck
```

### Run Desktop App

```bash
# Build Python sidecar first
./scripts/build-sidecar.sh

# Run Tauri app
cd ui
npm install
npm run tauri dev
```

## Connection Flow

1. Open Deck Link on both devices
2. On Device A: Enter Device B's IP address (or select from discovered devices)
3. Device B displays a passphrase (e.g., "pixel")
4. Device A enters the passphrase
5. Connected!

## Architecture

- **Frontend**: Tauri + React (TypeScript)
- **Backend**: Python sidecar (WebSocket server)
- **Discovery**: mDNS via Zeroconf
- **Port**: 52525

## Development

See [AGENTS.md](./AGENTS.md) for detailed development instructions.

## License

MIT
