import React from 'react';
import { AlertInfo } from '../services/detection.service';
import ThreatBadge from './ThreatBadge';
import { formatDateTime } from '../utils/formatDate';

function normalizeThreatScore(raw: number): number {
  if (!Number.isFinite(raw)) return 0;
  if (raw > 1 && raw <= 100) return Number((raw / 100).toFixed(4));
  if (raw < 0) return 0;
  if (raw > 1) return 1;
  return Number(raw.toFixed(4));
}

interface AlertListProps {
  alerts: AlertInfo[];
  loading: boolean;
}

const AlertList: React.FC<AlertListProps> = ({ alerts, loading }) => {
  if (loading) {
    return <p className="text-slate-500">Loading alerts...</p>;
  }

  if (alerts.length === 0) {
    return <p className="text-slate-500">No alerts at this time.</p>;
  }

  return (
    <div className="space-y-3 max-h-96 overflow-y-auto">
      {alerts.map((alert) => {
        const normalizedScore = normalizeThreatScore(alert.threat_score);
        return (
        <div
          key={alert.id}
          className={`p-3 border rounded-lg ${
            alert.is_read ? 'bg-panel border-edge' : 'bg-blue-500/10 border-blue-500/20'
          } ${alert.is_resolved ? 'opacity-60' : ''}`}
        >
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <ThreatBadge level={alert.threat_level} />
              <span className="font-medium text-sm text-slate-200">{alert.title}</span>
            </div>
            <span className="text-xs text-slate-500">
              {formatDateTime(alert.created_at)}
            </span>
          </div>
          {alert.description && (
            <p className="text-sm text-slate-400 mt-1">{alert.description}</p>
          )}
          <div className="flex gap-3 mt-1 text-xs text-slate-500">
            {alert.source && <span>Source: {alert.source}</span>}
            <span>Score: {normalizedScore.toFixed(3)}</span>
            {alert.is_resolved && <span className="text-green-400">Resolved</span>}
          </div>
        </div>
        );
      })}
    </div>
  );
};

export default AlertList;
