import { useState } from 'react';

interface PassphraseInputProps {
  peerName: string;
  onSubmit: (passphrase: string) => void;
  onCancel: () => void;
  error?: string | null;
}

export function PassphraseInput({ peerName, onSubmit, onCancel, error }: PassphraseInputProps) {
  const [passphrase, setPassphrase] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (passphrase.trim()) {
      onSubmit(passphrase.trim());
    }
  };

  return (
    <div className="container fade-in">
      <div className="text-center mb-6">
        <h1>Enter Passphrase</h1>
        <p className="mt-2">
          Connecting to <strong>{peerName}</strong>
        </p>
      </div>

      <div className="card mb-6">
        <p className="text-center mb-4">
          Enter the word shown on the other device:
        </p>
        
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            className="input input-lg mb-4"
            placeholder="passphrase"
            value={passphrase}
            onChange={(e) => setPassphrase(e.target.value.toLowerCase())}
            autoFocus
            autoComplete="off"
            autoCapitalize="off"
          />
          
          {error && (
            <p className="text-center mb-4" style={{ color: 'var(--accent-error)' }}>
              {error}
            </p>
          )}
          
          <div className="flex flex-col gap-3">
            <button
              type="submit"
              className="btn btn-primary btn-full"
              disabled={!passphrase.trim()}
            >
              Verify
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-full"
              onClick={onCancel}
            >
              Cancel
            </button>
          </div>
        </form>
      </div>

      <p className="text-center text-sm text-muted">
        Look at the other device's screen to find the passphrase.
      </p>
    </div>
  );
}
