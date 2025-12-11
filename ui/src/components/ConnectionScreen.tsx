import type { Peer, LocalInfo as LocalInfoType } from '../types';
import { LocalInfo } from './LocalInfo';
import { PeerList } from './PeerList';
import { ManualConnect } from './ManualConnect';

interface ConnectionScreenProps {
  localInfo: LocalInfoType | null;
  peers: Peer[];
  onConnect: (host: string, port: number) => void;
  isConnecting?: boolean;
}

export function ConnectionScreen({ localInfo, peers, onConnect, isConnecting }: ConnectionScreenProps) {
  const handlePeerSelect = (peer: Peer) => {
    onConnect(peer.host, peer.port);
  };

  return (
    <div className="container fade-in">
      <div className="text-center mb-6">
        <h1>Deck Link</h1>
        <p>Connect your devices</p>
      </div>

      <LocalInfo info={localInfo} />

      <div className="mt-6">
        <h3 className="mb-4">Discovered Devices</h3>
        <PeerList peers={peers} onSelect={handlePeerSelect} />
      </div>

      <div className="divider mt-6 mb-6">or connect manually</div>

      <ManualConnect onConnect={onConnect} disabled={isConnecting} />

      {isConnecting && (
        <div className="text-center mt-6">
          <div className="spin" style={{ 
            width: 24, 
            height: 24, 
            border: '3px solid var(--border-color)',
            borderTopColor: 'var(--accent-primary)',
            borderRadius: '50%',
            margin: '0 auto'
          }} />
          <p className="text-sm text-muted mt-2">Connecting...</p>
        </div>
      )}
    </div>
  );
}
