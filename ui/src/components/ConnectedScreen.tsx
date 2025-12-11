import type { Peer } from '../types';

interface ConnectedScreenProps {
  peer: Peer;
  onDisconnect: () => void;
}

export function ConnectedScreen({ peer, onDisconnect }: ConnectedScreenProps) {
  return (
    <div className="container fade-in">
      <div className="text-center mb-6">
        <h1>Connected!</h1>
        <p className="mt-2">You're linked and ready to go</p>
      </div>

      <div className="card connected-card mb-6">
        <div className="connection-status mb-4">
          <span className="status-dot connected" />
          <span>Active Connection</span>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="peer-icon">
            {peer.device_type === 'deck' ? '🎮' : '💻'}
          </div>
          <div className="peer-info">
            <div className="peer-name">{peer.name || 'Connected Device'}</div>
            <div className="peer-address">{peer.host}:{peer.port}</div>
          </div>
        </div>
      </div>

      <div className="card mb-6">
        <h3 className="mb-4">What's next?</h3>
        <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <li className="flex items-center gap-3">
            <span>📁</span>
            <span className="text-secondary">Transfer files between devices</span>
          </li>
          <li className="flex items-center gap-3">
            <span>🔔</span>
            <span className="text-secondary">Send notifications</span>
          </li>
          <li className="flex items-center gap-3">
            <span>🎮</span>
            <span className="text-secondary">Stream controller inputs</span>
          </li>
          <li className="flex items-center gap-3">
            <span>⌨️</span>
            <span className="text-secondary">Remote keyboard control</span>
          </li>
        </ul>
      </div>

      <button
        className="btn btn-danger btn-full"
        onClick={onDisconnect}
      >
        Disconnect
      </button>
    </div>
  );
}
