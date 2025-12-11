import type { Peer } from '../types';

interface PeerListProps {
  peers: Peer[];
  onSelect: (peer: Peer) => void;
}

export function PeerList({ peers, onSelect }: PeerListProps) {
  if (peers.length === 0) {
    return (
      <div className="text-center text-muted mt-4">
        <p>No devices found on network</p>
        <p className="text-sm mt-2">Make sure Deck Link is running on the other device</p>
      </div>
    );
  }

  return (
    <div className="peer-list">
      {peers.map((peer) => (
        <div
          key={`${peer.host}:${peer.port}`}
          className="card card-clickable peer-card"
          onClick={() => onSelect(peer)}
        >
          <div className="peer-icon">
            {peer.device_type === 'deck' ? '🎮' : '💻'}
          </div>
          <div className="peer-info">
            <div className="peer-name">{peer.name}</div>
            <div className="peer-address">{peer.host}:{peer.port}</div>
          </div>
          <span style={{ color: 'var(--accent-primary)' }}>→</span>
        </div>
      ))}
    </div>
  );
}
