import type { ConnectionState } from '../types';

interface HeaderProps {
  state: ConnectionState;
}

export function Header({ state }: HeaderProps) {
  const getStatusClass = () => {
    switch (state) {
      case 'connected':
        return 'connected';
      case 'awaiting_challenge':
      case 'challenge_sent':
      case 'awaiting_auth_input':
        return 'connecting';
      default:
        return 'disconnected';
    }
  };

  return (
    <header className="header">
      <div className="logo">
        <span>{"<>"}</span>
        <span>Deck Link</span>
      </div>
      <div className="flex items-center gap-2">
        <span className={`status-dot ${getStatusClass()}`} />
        <span className="text-sm text-muted">
          {state === 'connected' ? 'Connected' : state === 'disconnected' ? 'Offline' : 'Connecting...'}
        </span>
      </div>
    </header>
  );
}
