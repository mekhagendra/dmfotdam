import React from 'react';
import { AlertInfo } from '../services/detection.service';
import ThreatBadge from './ThreatBadge';

interface AlertListProps {
  alerts: AlertInfo[];
  loading: boolean;
}

const AlertList: React.FC<AlertListProps> = ({ alerts, loading }) => {
  if (loading) {
    return <p className="text-gray-500">Loading alerts...</p>;
  }

  if (alerts.length === 0) {
    return <p className="text-gray-500">No alerts at this time.</p>;
  }

  return (
    <div className="space-y-3 max-h-96 overflow-y-auto">
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className={`p-3 border rounded-lg ${
            alert.is_read ? 'bg-white' : 'bg-blue-50 border-blue-200'
          } ${alert.is_resolved ? 'opacity-60' : ''}`}
        >
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <ThreatBadge level={alert.threat_level} />
              <span className="font-medium text-sm">{alert.title}</span>
            </div>
            <span className="text-xs text-gray-400">
              {new Date(alert.created_at).toLocaleString()}
            </span>
          </div>
          {alert.description && (
            <p className="text-sm text-gray-600 mt-1">{alert.description}</p>
          )}
          <div className="flex gap-3 mt-1 text-xs text-gray-500">
            {alert.source && <span>Source: {alert.source}</span>}
            <span>Score: {alert.threat_score.toFixed(3)}</span>
            {alert.is_resolved && <span className="text-green-600">Resolved</span>}
          </div>
        </div>
      ))}
    </div>
  );
};

export default AlertList;
