import React, { useMemo, useState } from 'react';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useSourceDailyTrends, useSources } from '../hooks/useDetection';

const SOURCE_COLORS = [
  '#2563EB',
  '#16A34A',
  '#DC2626',
  '#9333EA',
  '#D97706',
  '#0D9488',
  '#DB2777',
  '#334155',
];

const Trends: React.FC = () => {
  const [days, setDays] = useState(30);
  const [selectedSourceId, setSelectedSourceId] = useState<string>('');
  const { data: sources = [] } = useSources();
  const { data: trendData, isLoading } = useSourceDailyTrends(days);

  const sourceMap = useMemo(() => {
    return new Map(sources.map((s) => [s.id, s]));
  }, [sources]);

  const filteredPoints = useMemo(() => {
    const points = trendData?.points || [];
    if (!selectedSourceId) {
      return points;
    }
    return points.filter((p) => p.source_id === selectedSourceId);
  }, [trendData?.points, selectedSourceId]);

  const dateLabels = useMemo(() => {
    return Array.from(new Set(filteredPoints.map((p) => p.date))).sort();
  }, [filteredPoints]);

  const sourceSeries = useMemo(() => {
    const ids = Array.from(new Set(filteredPoints.map((p) => p.source_id)));
    return ids.map((id) => ({
      id,
      name: sourceMap.get(id)?.name || id,
    }));
  }, [filteredPoints, sourceMap]);

  const chartData = useMemo(() => {
    const byDateAndSource = new Map<string, number>();
    for (const p of filteredPoints) {
      byDateAndSource.set(`${p.date}::${p.source_id}`, Number(p.avg_threat_score.toFixed(4)));
    }

    return dateLabels.map((date) => {
      const row: Record<string, string | number | null> = { date };
      for (const s of sourceSeries) {
        row[s.id] = byDateAndSource.has(`${date}::${s.id}`)
          ? byDateAndSource.get(`${date}::${s.id}`) || 0
          : null;
      }
      return row;
    });
  }, [filteredPoints, dateLabels, sourceSeries]);

  const overallAvgThreatScore =
    filteredPoints.length > 0
      ? filteredPoints.reduce((sum, p) => sum + p.avg_threat_score, 0) / filteredPoints.length
      : 0;

  const peakAvgThreatScore =
    filteredPoints.length > 0
      ? Math.max(...filteredPoints.map((p) => p.avg_threat_score))
      : 0;

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-slate-200 p-4 sm:p-5 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">Source Trends</h2>
            <p className="text-sm text-slate-600 mt-1">
              Daily trend analysis for user-added monitoring sources. One line per source.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="px-3 py-2 border border-slate-300 rounded-md text-sm bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500"
              aria-label="Days filter"
            >
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>

            <select
              value={selectedSourceId}
              onChange={(e) => setSelectedSourceId(e.target.value)}
              className="px-3 py-2 border border-slate-300 rounded-md text-sm bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500 min-w-[220px]"
              aria-label="Source filter"
            >
              <option value="">All Added Sources</option>
              {sources.map((source) => (
                <option key={source.id} value={source.id}>
                  {source.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-300 rounded-lg p-4">
          <p className="text-sm text-slate-600">Active series</p>
          <p className="text-2xl font-semibold text-slate-900 mt-1">{sourceSeries.length}</p>
        </div>
        <div className="bg-white border border-slate-300 rounded-lg p-4">
          <p className="text-sm text-slate-600">Days displayed</p>
          <p className="text-2xl font-semibold text-slate-900 mt-1">{dateLabels.length}</p>
        </div>
        <div className="bg-white border border-slate-300 rounded-lg p-4">
          <p className="text-sm text-slate-600">Overall avg threat score</p>
          <p className="text-2xl font-semibold text-slate-900 mt-1">{overallAvgThreatScore.toFixed(3)}</p>
        </div>
        <div className="bg-white border border-slate-300 rounded-lg p-4">
          <p className="text-sm text-slate-600">Peak daily avg score</p>
          <p className="text-2xl font-semibold text-slate-900 mt-1">{peakAvgThreatScore.toFixed(3)}</p>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-slate-300 p-4 sm:p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-900">Daily Source Trend (Average Threat Score)</h3>
          <span className="text-sm text-slate-600">X-axis: Day | Y-axis: Average threat score (0-1)</span>
        </div>

        {isLoading ? (
          <p className="text-slate-500 py-10 text-center">Loading trends...</p>
        ) : chartData.length === 0 ? (
          <div className="text-center py-10">
            <h4 className="text-base font-semibold text-slate-900 mb-1">No trend data available</h4>
            <p className="text-sm text-slate-600">Add sources and run scans to generate daily trends.</p>
          </div>
        ) : (
          <div className="w-full h-[420px] sm:h-[500px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 12, right: 16, left: 8, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="date" tick={{ fill: '#64748B', fontSize: 12 }} />
                <YAxis tick={{ fill: '#64748B', fontSize: 12 }} domain={[0, 1]} />
                <Tooltip
                  formatter={(value) => {
                    const numeric = typeof value === 'number' ? value : Number(value);
                    const label = Number.isFinite(numeric) ? numeric.toFixed(3) : '-';
                    return [label, 'Avg Threat Score'];
                  }}
                  contentStyle={{
                    backgroundColor: '#FFFFFF',
                    border: '1px solid #E2E8F0',
                    borderRadius: 8,
                  }}
                />
                <Legend />
                {sourceSeries.map((series, idx) => (
                  <Line
                    key={series.id}
                    type="linear"
                    dataKey={series.id}
                    name={series.name}
                    stroke={SOURCE_COLORS[idx % SOURCE_COLORS.length]}
                    strokeWidth={2.2}
                    dot={false}
                    connectNulls={false}
                    activeDot={{ r: 4 }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
};

export default Trends;
