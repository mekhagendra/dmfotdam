import React from 'react';
import SeverityBadge from './ui/SeverityBadge';

interface ThreatBadgeProps {
  level: string;
}

/**
 * Legacy wrapper around the new <SeverityBadge>. Existing imports
 * (`import ThreatBadge from '../components/ThreatBadge'`) keep working
 * while the new component owns the visual style.
 */
const ThreatBadge: React.FC<ThreatBadgeProps> = ({ level }) => (
  <SeverityBadge level={level} />
);

export default ThreatBadge;
