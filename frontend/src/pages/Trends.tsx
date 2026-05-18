import React, { useMemo, useState } from 'react';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useSourceDailyTrends, useSources } from '../hooks/useDetection';
import { Card, KPITile, PageHeader, LiveIndicator, EmptyState } from '../components/ui';

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
  const { data: trendData, isLoading, dataUpdatedAt } = useSourceDailyTrends(days);

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
      <PageHeader
        title="Source Trends"
        subtitle={
          <>
            <span>Daily trend analysis for user-added monitoring sources. One line per source.</span>
            <LiveIndicator dataUpdatedAt={dataUpdatedAt} />
          </>
        }
        actions={
          <>
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="h-9 px-3 text-sm border border-slate-200 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500"
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
              className="h-9 px-3 text-sm border border-slate-200 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500 min-w-[200px]"
              aria-label="Source filter"
            >
              <option value="">All Added Sources</option>
              {sources.map((source) => (
                <option key={source.id} value={source.id}>
                  {source.name}
                </option>
              ))}
            </select>
          </>
        }
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPITile label="Active series" value={sourceSeries.length} accent="blue" />
        <KPITile label="Days displayed" value={dateLabels.length} accent="purple" />
        <KPITile
          label="Overall avg threat"
          value={<span className="font-mono">{overallAvgThreatScore.toFixed(3)}</span>}
          accent="amber"
        />
        <KPITile
          label="Peak daily avg"
          value={<span className="font-mono">{peakAvgThreatScore.toFixed(3)}</span>}
          accent="red"
        />
      </div>

      <Card
        title="Daily Source Trend (Average Threat Score)"
        subtitle="X-axis: Day · Y-axis: Average threat score (0–1)"
        loading={isLoading}
      >
        {chartData.length === 0 ? (
          <EmptyState
            title="No trend data available"
            description="Add sources and run scans to generate daily trends."
          />
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
      </Card>
    </div>
  );
};

export default Trends;
