import React from 'react';

interface ThreatBadgeProps {
  level: string;
}

const levelColors: Record<string, string> = {
  critical: 'bg-red-500/20 text-red-400 border-red-500/30',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  low: 'bg-green-500/20 text-green-400 border-green-500/30',
};

const ThreatBadge: React.FC<ThreatBadgeProps> = ({ level }) => {
  const color = levelColors[level] || levelColors.low;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${color}`}>
      {level.toUpperCase()}
    </span>
  );
};

export default ThreatBadge;
