import React from 'react';

interface ThreatBadgeProps {
  level: string;
}

const levelColors: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 border-red-200',
  high: 'bg-orange-100 text-orange-800 border-orange-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  low: 'bg-green-100 text-green-800 border-green-200',
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
