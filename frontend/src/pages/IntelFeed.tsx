import React, { useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import ThreatBadge from '../components/ThreatBadge';
import { useAlerts, useCollectedItems, useResetScannedData, useRunScanNow, useSources } from '../hooks/useDetection';
import { formatDateTime } from '../utils/formatDate';
import { PageHeader, LiveIndicator } from '../components/ui';

const DURATION_OPTIONS = [
  { label: 'Last 24 hours', valueMs: 24 * 60 * 60 * 1000 },
  { label: 'Last 3 days', valueMs: 3 * 24 * 60 * 60 * 1000 },
  { label: 'Last 7 days', valueMs: 7 * 24 * 60 * 60 * 1000 },
  { label: 'Last 14 days', valueMs: 14 * 24 * 60 * 60 * 1000 },
  { label: 'Last 30 days', valueMs: 30 * 24 * 60 * 60 * 1000 },
  { label: 'Last 90 days', valueMs: 90 * 24 * 60 * 60 * 1000 },
];

const IntelFeed: React.FC = () => {
  const [durationFilterMs, setDurationFilterMs] = useState<number>(7 * 24 * 60 * 60 * 1000);
  const [selectedSourceName, setSelectedSourceName] = useState<string>('');
  const [selectedCriticality, setSelectedCriticality] = useState<string>('');
  const runScanMutation = useRunScanNow();
  const resetDataMutation = useResetScannedData();
  const { data: alerts, isLoading: alertsLoading, dataUpdatedAt: alertsUpdatedAt } = useAlerts();
  const { data: sources } = useSources();
  const location = useLocation();

  // Drill-through: accept `?source=` and `?severity=` from URL on mount.
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const src = params.get('source');
    const sev = params.get('severity');
    if (src) setSelectedSourceName(src);
    if (sev) setSelectedCriticality(sev);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const selectedDays = Math.max(1, Math.round(durationFilterMs / (24 * 60 * 60 * 1000)));
  const { data: collectedItems, isLoading: itemsLoading } = useCollectedItems(selectedDays, 300);

  const sourceOptions = useMemo(() => {
    return (sources || []).map((s) => ({
      id: s.id,
      name: s.name,
      type: s.source_type,
    }));
  }, [sources]);

  const filteredAlerts = useMemo(() => {
    const now = Date.now();
    const maxAgeMs = durationFilterMs;

    return (alerts || []).filter((alert) => {
      if (selectedSourceName) {
        const alertSourceName = alert.source_name || '';
        if (alertSourceName !== selectedSourceName) {
          return false;
        }
      }
      if (!alert.source_type) {
        return false;
      }
      if (selectedCriticality && alert.threat_level !== selectedCriticality) {
        return false;
      }
      const createdMs = Date.parse(alert.created_at);
      if (Number.isNaN(createdMs)) {
        return true;
      }
      return now - createdMs <= maxAgeMs;
    });
  }, [alerts, durationFilterMs, selectedSourceName, selectedCriticality]);

  const filteredItems = useMemo(() => {
    const items = collectedItems || [];
    return items.filter((item) => {
      if (selectedSourceName && item.source_name !== selectedSourceName) {
        return false;
      }
      if (selectedCriticality && item.threat_level !== selectedCriticality) {
        return false;
      }
      return true;
    });
  }, [collectedItems, selectedSourceName, selectedCriticality]);

  const combinedScannedSource = useMemo(() => {
    const alertRows = filteredAlerts.map((alert) => ({
      id: `alert-${alert.id}`,
      kind: 'alert' as const,
      title: alert.title,
      text: alert.description || '',
      sourceName: alert.source_name || alert.source || 'Unknown source',
      sourceType: alert.source_type || 'unknown',
      threatLevel: alert.threat_level,
      threatScore: alert.threat_score,
      when: alert.created_at,
      url: alert.source?.startsWith('http') ? alert.source : null,
      isResolved: alert.is_resolved,
    }));

    // Build a dedup key set from alerts: every high-threat collected item also
    // generates an alert, so without this check each item appears twice.
    const alertKeys = new Set(
      alertRows.map((r) => `${r.title}::${r.sourceName}`)
    );

    const itemRows = filteredItems
      .filter((item) => {
        const sourceName = item.source_name ?? '';
        return !alertKeys.has(`${item.title}::${sourceName}`);
      })
      .map((item) => ({
        id: `item-${item.id}`,
        kind: 'scan' as const,
        title: item.title,
        text: item.text || '',
        sourceName: item.source_name,
        sourceType: item.source_type,
        threatLevel: item.threat_level,
        threatScore: item.threat_score,
        when: item.collected_at,
        url: item.url,
        isResolved: false,
      }));

    return [...alertRows, ...itemRows].sort(
      (a, b) => Date.parse(b.when) - Date.parse(a.when),
    );
  }, [filteredAlerts, filteredItems]);

  const scanSummary = useMemo(() => {
    const data = runScanMutation.data as
      | { sources_polled?: number; scanned_at?: string; results?: Array<{ source?: string; fetched?: number; new?: number; error?: string }> }
      | undefined;
    if (!data) return null;

    const results = data.results || [];
    const fetchedTotal = results.reduce((sum, r) => sum + (typeof r.fetched === 'number' ? r.fetched : 0), 0);
    const newTotal = results.reduce((sum, r) => sum + (typeof r.new === 'number' ? r.new : 0), 0);
    const failed = results.filter((r) => !!r.error).length;

    return {
      polled: typeof data.sources_polled === 'number' ? data.sources_polled : 0,
      fetchedTotal,
      newTotal,
      failed,
      scannedAt: data.scanned_at ?? null,
      perSource: results,
    };
  }, [runScanMutation.data]);

  const handleResetData = () => {
    const confirmed = window.confirm(
      'Reset scanned data for your account? This will delete scanned items and alerts only. Your login and source settings will remain unchanged.',
    );
    if (!confirmed) {
      return;
    }
    resetDataMutation.mutate();
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Monitor"
        subtitle={
          <>
            <span>Live alerts and scanned items from your sources</span>
            <LiveIndicator dataUpdatedAt={alertsUpdatedAt} />
          </>
        }
        actions={
          <>
            <select
              value={durationFilterMs}
              onChange={(e) => setDurationFilterMs(Number(e.target.value))}
              className="h-9 px-3 text-sm border border-slate-200 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500"
              aria-label="Date range filter"
            >
              {DURATION_OPTIONS.map((opt) => (
                <option key={opt.valueMs} value={opt.valueMs}>
                  {opt.label}
                </option>
              ))}
            </select>
            <select
              value={selectedSourceName}
              onChange={(e) => setSelectedSourceName(e.target.value)}
              className="h-9 px-3 text-sm border border-slate-200 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500 min-w-[180px]"
              aria-label="Source filter"
            >
              <option value="">All Sources</option>
              {sourceOptions.map((source) => (
                <option key={source.id} value={source.name}>
                  {source.name}
                </option>
              ))}
            </select>
            <select
              value={selectedCriticality}
              onChange={(e) => setSelectedCriticality(e.target.value)}
              className="h-9 px-3 text-sm border border-slate-200 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500 min-w-[150px]"
              aria-label="Criticality filter"
            >
              <option value="">All Criticality</option>
              <option value="critical">CRITICAL</option>
              <option value="high">HIGH</option>
              <option value="medium">MEDIUM</option>
              <option value="low">LOW</option>
            </select>
            <button
              onClick={() => runScanMutation.mutate()}
              disabled={runScanMutation.isLoading}
              className="h-9 px-3 text-sm font-medium bg-primary-600 hover:bg-primary-700 text-white rounded-md disabled:opacity-50"
            >
              {runScanMutation.isLoading ? 'Running Scan...' : 'Run Scan Now'}
            </button>
            <button
              onClick={handleResetData}
              disabled={resetDataMutation.isLoading}
              className="h-9 px-3 text-sm font-medium bg-red-600 hover:bg-red-700 text-white rounded-md disabled:opacity-50"
            >
              {resetDataMutation.isLoading ? 'Resetting...' : 'Clear History'}
            </button>
          </>
        }
      />

      {sourceOptions.length === 0 && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
          <p className="text-sm text-blue-800">No sources added yet. Add sources from Source Settings to filter alerts by source.</p>
        </div>
      )}

      {scanSummary && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <p className="text-sm font-semibold text-emerald-800">
              Last scan completed{scanSummary.scannedAt ? ` — ${formatDateTime(scanSummary.scannedAt)}` : ''}
            </p>
            {scanSummary.newTotal === 0 && (
              <span className="text-xs text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">
                No new items (all content already indexed)
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-white border border-emerald-200 rounded-lg p-3">
              <p className="text-xs text-slate-600">Sources polled</p>
              <p className="text-xl font-semibold text-slate-900">{scanSummary.polled}</p>
            </div>
            <div className="bg-white border border-emerald-200 rounded-lg p-3">
              <p className="text-xs text-slate-600">Items fetched</p>
              <p className="text-xl font-semibold text-slate-900">{scanSummary.fetchedTotal}</p>
            </div>
            <div className="bg-white border border-emerald-200 rounded-lg p-3">
              <p className="text-xs text-slate-600">New items stored</p>
              <p className={`text-xl font-semibold ${scanSummary.newTotal > 0 ? 'text-emerald-700' : 'text-slate-500'}`}>
                {scanSummary.newTotal}
              </p>
            </div>
            <div className="bg-white border border-emerald-200 rounded-lg p-3">
              <p className="text-xs text-slate-600">Failed sources</p>
              <p className={`text-xl font-semibold ${scanSummary.failed > 0 ? 'text-red-600' : 'text-slate-500'}`}>
                {scanSummary.failed}
              </p>
            </div>
          </div>
          {scanSummary.perSource.length > 0 && (
            <div className="text-xs text-slate-600 space-y-1">
              {scanSummary.perSource.map((r, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${r.error ? 'bg-red-400' : 'bg-emerald-400'}`} />
                  <span className="font-medium">{r.source ?? `Source ${i + 1}`}:</span>
                  {r.error
                    ? <span className="text-red-600">{r.error}</span>
                    : <span>{r.fetched ?? 0} fetched, <strong>{r.new ?? 0} new</strong></span>
                  }
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-300 rounded-lg p-4">
          <p className="text-sm text-slate-600">Combined scanned source</p>
          <p className="text-2xl font-semibold text-slate-900 mt-1">{combinedScannedSource.length}</p>
        </div>
        <div className="bg-white border border-slate-300 rounded-lg p-4">
          <p className="text-sm text-slate-600">Alert records</p>
          <p className="text-2xl font-semibold text-slate-900 mt-1">
            {filteredAlerts.length}
          </p>
        </div>
        <div className="bg-white border border-slate-300 rounded-lg p-4">
          <p className="text-sm text-slate-600">High/Critical (combined)</p>
          <p className="text-2xl font-semibold text-slate-900 mt-1">
            {combinedScannedSource.filter((r) => r.threatLevel === 'high' || r.threatLevel === 'critical').length}
          </p>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-slate-300 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-900">Scanned Source</h3>
          <span className="text-sm text-slate-600">
            {runScanMutation.isLoading ? 'Scanning sources...' : 'Live from monitoring scans'}
          </span>
        </div>

        {(alertsLoading || itemsLoading) ? (
          <p className="text-slate-500 py-6 text-center">Loading scanned source data...</p>
        ) : combinedScannedSource.length === 0 ? (
          <div className="text-center py-8">
            <h4 className="text-base font-semibold text-slate-900 mb-1">No scanned source data for selected filters</h4>
            <p className="text-slate-600 text-sm">
              Add active sources in Monitoring, then click Run Scan Now to populate this feed.
            </p>
          </div>
        ) : (
          <div className="space-y-3 max-h-[560px] overflow-y-auto overflow-x-hidden">
            {combinedScannedSource.map((item) => (
              <div key={item.id} className={`p-3 border rounded-lg bg-white ${item.kind === 'alert' ? 'border-blue-200' : 'border-slate-200'}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1 overflow-hidden">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <ThreatBadge level={item.threatLevel} />
                      <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-700 uppercase tracking-wide">{item.sourceType}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded uppercase tracking-wide ${item.kind === 'alert' ? 'bg-blue-100 text-blue-700' : 'bg-emerald-100 text-emerald-700'}`}>
                        {item.kind === 'alert' ? 'Alert' : 'Scan'}
                      </span>
                      {item.isResolved && (
                        <span className="text-[10px] px-2 py-0.5 rounded uppercase tracking-wide bg-green-100 text-green-700">Resolved</span>
                      )}
                      <span className="text-xs text-slate-500 truncate">{item.sourceName}</span>
                    </div>
                    <p className="text-sm font-semibold text-slate-900 break-words line-clamp-2">{item.title}</p>
                    {item.text && <p className="text-xs text-slate-600 mt-1 break-words line-clamp-3">{item.text}</p>}
                    <div className="flex items-center gap-3 mt-2 text-xs text-slate-500 flex-wrap min-w-0">
                      <span>Score: {item.threatScore.toFixed(3)}</span>
                      <span>{item.kind === 'alert' ? 'Alerted' : 'Scanned'}: {formatDateTime(item.when)}</span>
                      {item.url && (
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-blue-600 hover:underline break-all max-w-full"
                        >
                          Open source
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default IntelFeed;
