interface ChallengeScreenProps {
  passphrase: string;
  peerName: string;
  onCancel: () => void;
}

export function ChallengeScreen({ passphrase, peerName, onCancel }: ChallengeScreenProps) {
  return (
    <div className="container fade-in">
      <div className="text-center mb-6">
        <h1>Connection Request</h1>
        <p className="mt-2">
          <strong>{peerName}</strong> wants to connect
        </p>
      </div>

      <div className="card mb-6">
        <p className="text-center mb-4">
          Tell them this passphrase:
        </p>
        <div className="passphrase-display">
          {passphrase}
        </div>
      </div>

      <p className="text-center text-sm text-muted mb-6">
        The other device must enter this word to connect.
        <br />
        This ensures you're connecting to the right device.
      </p>

      <button
        className="btn btn-secondary btn-full"
        onClick={onCancel}
      >
        Cancel
      </button>
    </div>
  );
}
