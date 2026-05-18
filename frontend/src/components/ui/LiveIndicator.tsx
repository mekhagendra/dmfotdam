import React, { useEffect, useState } from 'react';

export interface LiveIndicatorProps {
  /** When the bound query last updated (ms epoch). Use `dataUpdatedAt` from react-query. */
  dataUpdatedAt?: number;
  /** When false, hides the indicator (e.g. before first load) */
  active?: boolean;
  /** Optional override classes */
  className?: string;
}

function formatRelative(deltaMs: number): string {
  const sec = Math.max(0, Math.round(deltaMs / 1000));
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  return `${hr}h ago`;
}

/**
 * Small "Live · 12s ago" pill with a pulsing green dot. Ticks every second.
 */
const LiveIndicator: React.FC<LiveIndicatorProps> = ({
  dataUpdatedAt,
  active = true,
  className = '',
}) => {
  const [now, setNow] = useState<number>(() => Date.now());

  useEffect(() => {
    if (!active) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [active]);

  if (!active) return null;
  const label = dataUpdatedAt ? `Live · ${formatRelative(now - dataUpdatedAt)}` : 'Live';

  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs text-slate-600 ${className}`}
      aria-live="polite"
    >
      <span className="relative inline-flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60 animate-ping" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
      </span>
      {label}
    </span>
  );
};

export default LiveIndicator;
