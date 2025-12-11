import { useState, useEffect, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import type { ConnectionState, Peer, LocalInfo, ChallengeData, PassphraseRequiredData } from '../types';

interface ConnectionHook {
  state: ConnectionState;
  localInfo: LocalInfo | null;
  peers: Peer[];
  connectedPeer: Peer | null;
  challengePassphrase: string | null;
  challengePeerName: string | null;
  error: string | null;
  
  connect: (host: string, port: number) => Promise<void>;
  submitPassphrase: (passphrase: string) => Promise<void>;
  disconnect: () => Promise<void>;
  refreshPeers: () => Promise<void>;
  refreshStatus: () => Promise<void>;
}

export function useConnection(): ConnectionHook {
  const [state, setState] = useState<ConnectionState>('disconnected');
  const [localInfo, setLocalInfo] = useState<LocalInfo | null>(null);
  const [peers, setPeers] = useState<Peer[]>([]);
  const [connectedPeer, setConnectedPeer] = useState<Peer | null>(null);
  const [challengePassphrase, setChallengePassphrase] = useState<string | null>(null);
  const [challengePeerName, setChallengePeerName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Refresh status from backend
  const refreshStatus = useCallback(async () => {
    try {
      const status = await invoke<any>('get_status');
      if (status?.result) {
        setState(status.result.state || 'disconnected');
        setLocalInfo(status.result.local_info || null);
        if (status.result.peer) {
          setConnectedPeer(status.result.peer);
        }
      }
    } catch (err) {
      console.error('Failed to get status:', err);
    }
  }, []);

  // Refresh peer list
  const refreshPeers = useCallback(async () => {
    try {
      const result = await invoke<any>('get_peers');
      if (result?.result && Array.isArray(result.result)) {
        setPeers(result.result);
      }
    } catch (err) {
      console.error('Failed to get peers:', err);
    }
  }, []);

  // Connect to a peer
  const connect = useCallback(async (host: string, port: number) => {
    try {
      setError(null);
      setState('awaiting_challenge');
      await invoke('connect_to_peer', { host, port });
    } catch (err) {
      setError(String(err));
      setState('error');
    }
  }, []);

  // Submit passphrase
  const submitPassphrase = useCallback(async (passphrase: string) => {
    try {
      setError(null);
      await invoke('submit_passphrase', { passphrase });
    } catch (err) {
      setError(String(err));
    }
  }, []);

  // Disconnect
  const disconnect = useCallback(async () => {
    try {
      await invoke('disconnect_peer');
      setState('disconnected');
      setConnectedPeer(null);
      setChallengePassphrase(null);
      setChallengePeerName(null);
    } catch (err) {
      console.error('Disconnect error:', err);
    }
  }, []);

  // Set up event listeners
  useEffect(() => {
    const unlisteners: Array<() => void> = [];

    // State changed event
    listen<{ old_state: string; new_state: ConnectionState }>('sidecar:state_changed', (event) => {
      setState(event.payload.new_state);
    }).then((unlisten) => unlisteners.push(unlisten));

    // Challenge generated (we are receiving a connection)
    listen<ChallengeData>('sidecar:challenge_generated', (event) => {
      setChallengePassphrase(event.payload.passphrase);
      setChallengePeerName(event.payload.peer_name);
      setState('challenge_sent');
    }).then((unlisten) => unlisteners.push(unlisten));

    // Passphrase required (we are initiating a connection)
    listen<PassphraseRequiredData>('sidecar:passphrase_required', (event) => {
      setChallengePeerName(event.payload.peer_name);
      setState('awaiting_auth_input');
    }).then((unlisten) => unlisteners.push(unlisten));

    // Connected
    listen<{ peer_name: string; peer_ip: string }>('sidecar:connected', (event) => {
      setState('connected');
      setConnectedPeer({
        name: event.payload.peer_name,
        host: event.payload.peer_ip,
        port: 52525,
        device_type: 'laptop',
      });
      setChallengePassphrase(null);
      setChallengePeerName(null);
    }).then((unlisten) => unlisteners.push(unlisten));

    // Disconnected
    listen('sidecar:disconnected', () => {
      setState('disconnected');
      setConnectedPeer(null);
      setChallengePassphrase(null);
      setChallengePeerName(null);
    }).then((unlisten) => unlisteners.push(unlisten));

    // Auth failed
    listen<{ reason: string }>('sidecar:auth_failed', (event) => {
      setError(event.payload.reason);
      setState('disconnected');
    }).then((unlisten) => unlisteners.push(unlisten));

    // Connection error
    listen<{ error: string }>('sidecar:connection_error', (event) => {
      setError(event.payload.error);
      setState('error');
    }).then((unlisten) => unlisteners.push(unlisten));

    // Notification from peer
    listen<{ title: string; body: string }>('sidecar:notification', async (event) => {
      // Use Tauri's notification plugin
      try {
        const { sendNotification } = await import('@tauri-apps/plugin-notification');
        await sendNotification({
          title: event.payload.title,
          body: event.payload.body,
        });
      } catch (err) {
        console.error('Failed to send notification:', err);
      }
    }).then((unlisten) => unlisteners.push(unlisten));

    // Initial status fetch
    refreshStatus();
    refreshPeers();

    // Poll for peers periodically
    const peerInterval = setInterval(refreshPeers, 5000);

    return () => {
      unlisteners.forEach((unlisten) => unlisten());
      clearInterval(peerInterval);
    };
  }, [refreshStatus, refreshPeers]);

  return {
    state,
    localInfo,
    peers,
    connectedPeer,
    challengePassphrase,
    challengePeerName,
    error,
    connect,
    submitPassphrase,
    disconnect,
    refreshPeers,
    refreshStatus,
  };
}
