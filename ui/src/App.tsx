import { Header } from './components/Header';
import { ConnectionScreen } from './components/ConnectionScreen';
import { ChallengeScreen } from './components/ChallengeScreen';
import { PassphraseInput } from './components/PassphraseInput';
import { ConnectedScreen } from './components/ConnectedScreen';
import { useConnection } from './hooks/useConnection';
import './index.css';

function App() {
  const {
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
  } = useConnection();

  const renderScreen = () => {
    switch (state) {
      case 'challenge_sent':
        // We're displaying passphrase for someone connecting to us
        return (
          <ChallengeScreen
            passphrase={challengePassphrase || ''}
            peerName={challengePeerName || 'Unknown Device'}
            onCancel={disconnect}
          />
        );

      case 'awaiting_auth_input':
        // We need to enter the passphrase shown on the other device
        return (
          <PassphraseInput
            peerName={challengePeerName || 'Unknown Device'}
            onSubmit={submitPassphrase}
            onCancel={disconnect}
            error={error}
          />
        );

      case 'connected':
        // We're connected!
        return (
          <ConnectedScreen
            peer={connectedPeer || { name: 'Unknown', host: '', port: 52525, device_type: 'laptop' }}
            onDisconnect={disconnect}
          />
        );

      case 'disconnected':
      case 'error':
      case 'awaiting_challenge':
      default:
        // Default connection screen
        return (
          <ConnectionScreen
            localInfo={localInfo}
            peers={peers}
            onConnect={connect}
            isConnecting={state === 'awaiting_challenge'}
          />
        );
    }
  };

  return (
    <div className="flex flex-col" style={{ minHeight: '100vh' }}>
      <Header state={state} />
      <main className="flex-1">
        {renderScreen()}
      </main>
    </div>
  );
}

export default App;
