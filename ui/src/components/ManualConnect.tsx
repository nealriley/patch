import { useState } from 'react';

interface ManualConnectProps {
  onConnect: (host: string, port: number) => void;
  disabled?: boolean;
}

export function ManualConnect({ onConnect, disabled }: ManualConnectProps) {
  const [address, setAddress] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Parse address (supports "host:port" or just "host")
    const parts = address.trim().split(':');
    const host = parts[0];
    const port = parts[1] ? parseInt(parts[1], 10) : 52525;
    
    if (host) {
      onConnect(host, port);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <input
        type="text"
        className="input"
        placeholder="Enter IP address (e.g., 192.168.1.100)"
        value={address}
        onChange={(e) => setAddress(e.target.value)}
        disabled={disabled}
      />
      <button
        type="submit"
        className="btn btn-primary btn-full"
        disabled={disabled || !address.trim()}
      >
        Connect
      </button>
    </form>
  );
}
