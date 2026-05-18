import React from 'react';
import { SEVERITY_STYLES, normalizeSeverity } from './severity';

export interface SeverityBadgeProps {
  /** Severity level — case-insensitive, falls back to 'low' if unknown */
  level: string;
  /** Visual size variant */
  size?: 'sm' | 'md';
  /** Optional override classes */
  className?: string;
}

/**
 * Pill badge that pairs severity color with its text label so color is
 * never the only signal. Uses the central severity color map.
 */
const SeverityBadge: React.FC<SeverityBadgeProps> = ({
  level,
  size = 'md',
  className = '',
}) => {
  const lvl = normalizeSeverity(level);
  const style = SEVERITY_STYLES[lvl];
  const sizeClass = size === 'sm' ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2 py-0.5';

  return (
    <span
      className={`inline-flex items-center font-semibold uppercase tracking-wide rounded ${sizeClass} ${style.badgeClass} ${className}`}
    >
      {lvl}
    </span>
  );
};

export default SeverityBadge;
