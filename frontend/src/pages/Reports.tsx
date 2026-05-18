import React, { useState, useCallback } from 'react';
import { useReports } from '../hooks/useDetection';
import ThreatBadge from '../components/ThreatBadge';
import { highlightKeywords } from '../utils/highlight';
import { AnalysisResult } from '../services/detection.service';
import { formatDateTime, getSydneyDateForFilename } from '../utils/formatDate';

const Reports: React.FC = () => {
  const { data: reports, isLoading } = useReports();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggle = (id: string) =>
    setExpandedId((prev) => (prev === id ? null : id));

  const exportCSV = useCallback(() => {
    if (!reports || reports.length === 0) return;

    const headers = [
      'id',
      'analysis_type',
      'status',
      'threat_score',
      'threat_level',
      'model_scores',
      'sentiment',
      'language',
      'keywords',
      'created_at',
    ];

    const escape = (v: string) => `"${v.replace(/"/g, '""')}"`;

    const rows = reports.map((r: AnalysisResult) =>
      [
        r.id,
        r.analysis_type,
        r.status,
        r.threat_score?.toFixed(4) ?? '',
        r.threat_level ?? '',
        r.model_scores ? JSON.stringify(r.model_scores) : '',
        r.sentiment ?? '',
        r.language ?? '',
        (r.keywords ?? []).join('; '),
        r.created_at,
      ]
        .map((v) => escape(String(v)))
        .join(','),
    );

    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `tdm-reports-${getSydneyDateForFilename()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }, [reports]);

  return (
    <div className="space-y-6">
      <div className="bg-panel rounded-lg border border-edge p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-slate-100">Analysis Reports</h2>
          {reports && reports.length > 0 && (
            <button
              onClick={exportCSV}
              className="text-sm px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-700 text-white border border-blue-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 focus:ring-offset-slate-100"
            >
              Export CSV
            </button>
          )}
        </div>

        {isLoading ? (
          <p className="text-slate-500">Loading reports...</p>
        ) : reports && reports.length > 0 ? (
          <div className="space-y-4">
            {reports.map((report) => {
              const isExpanded = expandedId === report.id;
              const keywords = report.keywords ?? [];
              const modelScoreEntries = Object.entries(report.model_scores ?? {}).sort(
                (a, b) => Number(b[1]) - Number(a[1]),
              );
              const rowModelNames = Array.from(
                new Set(
                  (report.row_results ?? []).flatMap((row) =>
                    Object.keys(row.model_scores ?? {}),
                  ),
                ),
              ).sort();

              return (
                <div
                  key={report.id}
                  className="border border-edge rounded-lg hover:bg-panel-hover transition-colors"
                >
                  {/* Clickable header row */}
                  <button
                    type="button"
                    onClick={() => toggle(report.id)}
                    className="w-full text-left p-4 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3 flex-wrap">
                      <span className="text-sm font-medium text-slate-500">
                        #{report.id.slice(0, 8)}
                      </span>
                      <span className="text-xs bg-slate-700/50 text-slate-300 px-2 py-0.5 rounded uppercase">
                        {report.analysis_type}
                      </span>
                      <ThreatBadge level={report.threat_level || 'low'} />
                      <span
                        className={`text-xs px-2 py-0.5 rounded ${
                          report.status === 'completed'
                            ? 'bg-green-500/15 text-green-400'
                            : report.status === 'failed'
                            ? 'bg-red-500/15 text-red-400'
                            : 'bg-yellow-500/15 text-yellow-400'
                        }`}
                      >
                        {report.status}
                      </span>
                      {report.threat_score !== null && (
                        <span className="text-xs text-slate-500">
                          Score: <strong>{report.threat_score.toFixed(4)}</strong>
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500">
                        {formatDateTime(report.created_at)}
                      </span>
                      <span
                        className={`transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                      >
                        ▾
                      </span>
                    </div>
                  </button>

                  {/* Expandable body */}
                  {isExpanded && (
                    <div className="px-4 pb-4 border-t border-edge pt-3 space-y-3">
                      <>
                      {report.summary && (
                        <div>
                          <h4 className="text-xs font-semibold text-slate-500 mb-1">
                            Summary
                          </h4>
                          <p className="text-sm text-slate-300">
                            {keywords.length > 0
                              ? highlightKeywords(report.summary, keywords)
                              : report.summary}
                          </p>
                        </div>
                      )}

                      <div className="flex flex-wrap gap-4 text-sm">
                        {report.sentiment && (
                          <span className="text-slate-400">
                            Sentiment: <strong>{report.sentiment}</strong>
                          </span>
                        )}
                        {report.language && (
                          <span className="text-slate-400">
                            Language: <strong>{report.language}</strong>
                          </span>
                        )}
                      </div>

                      {modelScoreEntries.length > 0 && (
                        <div>
                          <h4 className="text-xs font-semibold text-slate-500 mb-1">
                            Model Scores
                          </h4>
                          <div className="overflow-x-auto border border-edge rounded">
                            <table className="min-w-full text-xs">
                              <thead className="bg-panel-alt">
                                <tr>
                                  <th className="px-3 py-2 text-left font-semibold text-slate-400">Model</th>
                                  <th className="px-3 py-2 text-left font-semibold text-slate-400">Score</th>
                                </tr>
                              </thead>
                              <tbody>
                                {modelScoreEntries.map(([modelName, score]) => (
                                  <tr key={modelName} className="border-t border-edge">
                                    <td className="px-3 py-2 text-slate-300">{modelName}</td>
                                    <td className="px-3 py-2 text-cyan-300 font-medium">
                                      {Number(score).toFixed(4)}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      {report.row_results && report.row_results.length > 0 && rowModelNames.length > 0 && (
                        <div>
                          <h4 className="text-xs font-semibold text-slate-500 mb-1">
                            Message-wise Model Scores
                          </h4>
                          <div className="overflow-x-auto border border-edge rounded">
                            <table className="min-w-full text-xs">
                              <thead className="bg-panel-alt">
                                <tr>
                                  <th className="px-3 py-2 text-left font-semibold text-slate-400">Row</th>
                                  <th className="px-3 py-2 text-left font-semibold text-slate-400">Message</th>
                                  <th className="px-3 py-2 text-left font-semibold text-slate-400">Overall</th>
                                  {rowModelNames.map((modelName) => (
                                    <th
                                      key={modelName}
                                      className="px-3 py-2 text-left font-semibold text-slate-400 whitespace-nowrap"
                                    >
                                      {modelName}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {report.row_results.slice(0, 50).map((row) => (
                                  <tr key={row.row} className="border-t border-edge align-top">
                                    <td className="px-3 py-2 text-slate-500">{row.row}</td>
                                    <td className="px-3 py-2 text-slate-300 max-w-md">
                                      {row.message?.length > 120
                                        ? `${row.message.slice(0, 120)}...`
                                        : row.message}
                                    </td>
                                    <td className="px-3 py-2 text-slate-300">
                                      {Number(row.threat_score).toFixed(4)}
                                    </td>
                                    {rowModelNames.map((modelName) => {
                                      const score = row.model_scores?.[modelName];
                                      return (
                                        <td key={modelName} className="px-3 py-2 text-slate-300">
                                          {typeof score === 'number' ? score.toFixed(4) : '-'}
                                        </td>
                                      );
                                    })}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                          {report.row_results.length > 50 && (
                            <p className="text-xs text-slate-500 mt-2">
                              Showing first 50 rows in report view.
                            </p>
                          )}
                        </div>
                      )}

                      {keywords.length > 0 && (
                        <div>
                          <h4 className="text-xs font-semibold text-slate-500 mb-1">
                            Keywords
                          </h4>
                          <div className="flex flex-wrap gap-1">
                            {keywords.slice(0, 15).map((kw, i) => (
                              <span
                                key={i}
                                className="text-xs bg-blue-500/15 text-blue-400 px-2 py-0.5 rounded"
                              >
                                {kw}
                              </span>
                            ))}
                            {keywords.length > 15 && (
                              <span className="text-xs text-slate-500">
                                +{keywords.length - 15} more
                              </span>
                            )}
                          </div>
                        </div>
                      )}

                      {report.details &&
                        report.details.categories_detected && (
                          <div>
                          <h4 className="text-xs font-semibold text-slate-500 mb-1">
                              Categories
                            </h4>
                            <div className="flex flex-wrap gap-1">
                              {(
                                report.details.categories_detected as string[]
                              ).map((cat: string, i: number) => (
                                <span
                                  key={i}
                                  className="text-xs bg-orange-500/15 text-orange-400 px-2 py-0.5 rounded"
                                >
                                  {cat}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                      {report.explanation && (
                        <div>
                          <h4 className="text-xs font-semibold text-slate-500 mb-1">
                            Explanation (SHAP)
                          </h4>
                          <pre className="text-xs bg-panel-alt p-2 rounded overflow-x-auto max-h-40 text-slate-400">
                            {JSON.stringify(report.explanation, null, 2)}
                          </pre>
                        </div>
                      )}
                      </>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-slate-500">
            No analysis reports yet. Upload a document or analyze text to get
            started.
          </p>
        )}
      </div>
    </div>
  );
};

export default Reports;
