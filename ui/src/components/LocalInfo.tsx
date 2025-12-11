import type { LocalInfo as LocalInfoType } from '../types';

interface LocalInfoProps {
  info: LocalInfoType | null;
}

export function LocalInfo({ info }: LocalInfoProps) {
  if (!info) {
    return (
      <div className="local-info">
        <div className="label">Your Address</div>
        <div className="value">Loading...</div>
      </div>
    );
  }

  return (
    <div className="local-info">
      <div className="label">Your Address</div>
      <div className="value">{info.ip}:{info.port}</div>
    </div>
  );
}
