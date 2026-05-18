import React from 'react';
import { SEVERITY_STYLES, normalizeSeverity } from './severity';

export interface SeverityRailProps {
  /** Severity level — case-insensitive, falls back to 'low' if unknown */
  level: string;
  /** Optional override classes */
  className?: string;
}

/**
 * 4px-wide full-height vertical rail used as the left edge of alert rows.
 */
const SeverityRail: React.FC<SeverityRailProps> = ({ level, className = '' }) => {
  const style = SEVERITY_STYLES[normalizeSeverity(level)];
  return (
    <span
      aria-hidden="true"
      className={`block w-1 self-stretch rounded-l ${style.railClass} ${className}`}
    />
  );
};

export default SeverityRail;
