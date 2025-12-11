# Deck-Link Agent Instructions

A bidirectional communication bridge between Steam Deck and Linux laptop.

## Overview

Deck-Link enables real-time data transfer between a Steam Deck and a Linux laptop over local network. Both systems run a Tauri desktop app with a Python sidecar for networking.

## Architecture

```
┌─────────────────────────────────────┐         ┌─────────────────────────────────────┐
│           LAPTOP                    │         │         STEAM DECK                  │
│  ┌───────────────────────────────┐  │         │  ┌───────────────────────────────┐  │
│  │      Tauri App (UI)           │  │         │  │      Tauri App (UI)           │  │
│  │  - React frontend             │  │         │  │  - React frontend             │  │
│  │  - Touch-friendly, playful    │  │         │  │  - Touch-friendly, playful    │  │
│  └──────────────┬────────────────┘  │         │  └──────────────┬────────────────┘  │
│                 │ IPC                │         │                 │ IPC                │
│  ┌──────────────▼────────────────┐  │         │  ┌──────────────▼────────────────┐  │
│  │     Python Sidecar            │  │◄───────►│  │     Python Sidecar            │  │
│  │  - WebSocket server (:52525)  │  │  mDNS   │  │  - WebSocket server (:52525)  │  │
│  │  - mDNS discovery             │  │   +     │  │  - mDNS discovery             │  │
│  │  - Connection management      │  │  WS     │  │  - Connection management      │  │
│  └───────────────────────────────┘  │         │  └───────────────────────────────┘  │
└─────────────────────────────────────┘         └─────────────────────────────────────┘
```

## Project Structure

```
deck-link/
├── AGENTS.md
├── README.md
├── pyproject.toml
│
├── src/                          # Python sidecar
│   └── deck_link/
│       ├── __init__.py           # Constants (PORT=52525, SERVICE_TYPE)
│       ├── main.py               # CLI & JSON-RPC IPC server
│       ├── server.py             # WebSocket server, connection state machine
│       ├── discovery.py          # mDNS (zeroconf) - _decklink._tcp
│       ├── protocol.py           # Message types & serialization
│       ├── passphrase.py         # Random word generator
│       └── handlers/             # Future: file, keyboard, controller, audio
│
├── ui/                           # Tauri application
│   ├── package.json
│   ├── src-tauri/
│   │   ├── Cargo.toml
│   │   ├── tauri.conf.json
│   │   ├── src/main.rs           # Tauri commands, sidecar management
│   │   └── binaries/             # Python sidecar binary (built)
│   │
│   └── src/                      # React frontend
│       ├── App.tsx               # Main app with state routing
│       ├── index.css             # Global styles (techy, touch-friendly)
│       ├── types/index.ts        # TypeScript types
│       ├── hooks/
│       │   └── useConnection.ts  # Connection state hook
│       └── components/
│           ├── Header.tsx
│           ├── ConnectionScreen.tsx
│           ├── ChallengeScreen.tsx
│           ├── PassphraseInput.tsx
│           └── ConnectedScreen.tsx
│
├── scripts/
│   └── build-sidecar.sh          # Build Python as binary for Tauri
│
└── tests/
```

## Connection Flow

```
   INITIATOR (Client A)                         RECEIVER (Client B)
   ─────────────────────                        ────────────────────
         │                                              │
         │  1. User enters IP:port or selects           │
         │     from mDNS discovered peers               │
         │                                              │
         │──────── CONNECTION_REQUEST ─────────────────►│
         │                                              │
         │                                    2. Generate random word
         │                                       (e.g., "pixel")
         │                                       Display on screen
         │                                              │
         │◄─────── CHALLENGE_RESPONSE ─────────────────│
         │         (session_id)                         │
         │                                              │
   3. UI prompts user:                                  │
      "Enter passphrase from                            │
       other device"                                    │
         │                                              │
         │──────── AUTH_ATTEMPT ───────────────────────►│
         │         (session_id, passphrase)             │
         │                                              │
         │                                    4. Verify passphrase
         │                                              │
         │◄─────── AUTH_RESULT ────────────────────────│
         │         (success/failure)                    │
         │                                              │
   5. CONNECTED (bidirectional)              CONNECTED (bidirectional)
```

## Data Types (Current & Planned)

| Type | Direction | Status |
|------|-----------|--------|
| Connection/Auth | Bidirectional | Implemented |
| Ping/Pong | Bidirectional | Implemented |
| Notifications | Bidirectional | Implemented |
| Files/Folders | Bidirectional | Planned |
| Key Presses | Laptop → Deck | Planned |
| Controller Input | Deck → Laptop | Planned |
| Microphone (Live) | Bidirectional | Planned |

## Development Commands

```bash
# === Python Backend ===

# Install Python dependencies
cd ~/Code/deck-link
pip install -e ".[dev]"

# Run Python backend (CLI mode for testing)
deck-link run --mode laptop
deck-link run --mode deck

# Scan for peers
deck-link scan

# Connect via CLI
deck-link connect 192.168.1.100

# === Tauri App ===

# Install UI dependencies
cd ~/Code/deck-link/ui
npm install

# Build Python sidecar (required before Tauri)
cd ~/Code/deck-link
./scripts/build-sidecar.sh

# Run Tauri in dev mode
cd ~/Code/deck-link/ui
npm run tauri dev

# Build Tauri app
npm run tauri build
```

## Key Files

| File | Purpose |
|------|---------|
| `src/deck_link/protocol.py` | Message types (CONNECTION_REQUEST, AUTH_*, PING, etc.) |
| `src/deck_link/server.py` | WebSocket server, state machine, event emission |
| `src/deck_link/passphrase.py` | Tech-themed word list for passphrases |
| `ui/src/hooks/useConnection.ts` | React hook managing connection state |
| `ui/src-tauri/src/main.rs` | Tauri commands, sidecar process management |

## Network Details

- **Port**: 52525
- **Protocol**: WebSocket (JSON messages)
- **mDNS Service**: `_decklink._tcp.local.`
- **Discovery**: Automatic via Zeroconf/Avahi

## Steam Deck Deployment

1. Enable SSH on Steam Deck (Desktop Mode):
   ```bash
   passwd  # Set password for deck user
   sudo systemctl enable --now sshd
   ```

2. Copy the built Tauri app to Steam Deck:
   ```bash
   scp -r ui/src-tauri/target/release/bundle/appimage/*.AppImage deck@<ip>:~/
   ```

3. Run on Steam Deck:
   ```bash
   chmod +x ~/Deck-Link.AppImage
   ./Deck-Link.AppImage
   ```
