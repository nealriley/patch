export type ConnectionState =
  | 'disconnected'
  | 'awaiting_challenge'
  | 'challenge_sent'
  | 'awaiting_auth_input'
  | 'connected'
  | 'error';

export interface Peer {
  name: string;
  host: string;
  port: number;
  device_type: 'laptop' | 'deck';
}

export interface LocalInfo {
  name: string;
  type: string;
  ip: string;
  port: number;
}

export interface Status {
  state: ConnectionState;
  device_name: string;
  device_type: string;
  port: number;
  peer: Peer | null;
  session_id: string | null;
  local_info?: LocalInfo;
}

export interface ChallengeData {
  session_id: string;
  passphrase: string;
  peer_name: string;
}

export interface PassphraseRequiredData {
  session_id: string;
  peer_name: string;
}
