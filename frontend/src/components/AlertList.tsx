import React from 'react';
import { AlertInfo } from '../services/detection.service';
import { SeverityRail, SeverityBadge, EmptyState, normalizeSeverity } from './ui';
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
    return (
      <div className="space-y-2">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-12 bg-slate-100 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <EmptyState title="No active alerts" description="Alerts will appear here as they are triggered." />
    );
  }

  return (
    <ul className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
      {alerts.map((alert) => {
        const normalizedScore = normalizeThreatScore(alert.threat_score);
        const lvl = normalizeSeverity(alert.threat_level);
        return (
          <li
            key={alert.id}
            className={`flex items-stretch border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors overflow-hidden ${
              alert.is_resolved ? 'opacity-60' : ''
            }`}
          >
            <SeverityRail level={lvl} />
            <div className="flex-1 min-w-0 px-3 py-2">
              <div className="flex items-center justify-between gap-2 mb-1">
                <div className="flex items-center gap-2 min-w-0">
                  <SeverityBadge level={lvl} size="sm" />
                  <span className="font-medium text-sm text-slate-900 truncate">{alert.title}</span>
                </div>
                <span className="text-xs text-slate-500 flex-shrink-0">
                  {formatDateTime(alert.created_at)}
                </span>
              </div>
              {alert.description && (
                <p className="text-xs text-slate-600 mb-1 line-clamp-2">{alert.description}</p>
              )}
              <div className="flex gap-3 text-xs text-slate-500 flex-wrap">
                {alert.source && <span className="truncate">Source: {alert.source}</span>}
                <span>
                  Score: <span className="font-mono">{normalizedScore.toFixed(3)}</span>
                </span>
                {alert.is_resolved && <span className="text-green-600">Resolved</span>}
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
};

export default AlertList;
