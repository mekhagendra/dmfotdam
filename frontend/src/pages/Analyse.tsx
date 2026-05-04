import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useUploadDocument, useAnalyzeText, useUploadHistory, useAvailableModels } from '../hooks/useDetection';
import { AnalysisResult, RowResult, detectionService } from '../services/detection.service';
import ThreatBadge from '../components/ThreatBadge';
import { formatDate } from '../utils/formatDate';

const LEVEL_COLOR: Record<string, string> = {
  critical: '#DC2626',
  high: '#D97706',
  medium: '#CA8A04',
  low: '#16A34A',
};

const ModelSelector: React.FC<{
  models: { id: string; name: string; description: string; available?: string }[];
  selected: string[];
  onChange: (ids: string[]) => void;
}> = ({ models, selected, onChange }) => {
  const toggle = (id: string, isAvailable: boolean) => {
    if (!isAvailable) return;
    if (id === 'all') {
      onChange(['all']);
      return;
    }
    const next = selected.filter((s) => s !== 'all');
    onChange(next.includes(id) ? next.filter((s) => s !== id) : [...next, id]);
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      {models.map((m) => {
        const isAvailable = m.available !== 'false';
        const active = selected.includes(m.id) && isAvailable;
        return (
          <button
            key={m.id}
            type="button"
            onClick={() => toggle(m.id, isAvailable)}
            title={isAvailable ? m.description : 'Model not trained yet — use the Train Models panel to train it first'}
            style={{
              padding: '12px 14px',
              borderRadius: 8,
              border: `2px solid ${active ? '#2563EB' : isAvailable ? '#E2E8F0' : '#F1F5F9'}`,
              background: active ? '#EFF6FF' : isAvailable ? '#FFFFFF' : '#F8FAFC',
              textAlign: 'left',
              cursor: isAvailable ? 'pointer' : 'not-allowed',
              opacity: isAvailable ? 1 : 0.55,
              transition: 'all 0.15s',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontWeight: 600, color: active ? '#1D4ED8' : isAvailable ? '#1E293B' : '#94A3B8', fontSize: 13 }}>{m.name}</span>
              {!isAvailable && (
                <span style={{ fontSize: 10, background: '#FEF3C7', color: '#92400E', borderRadius: 4, padding: '1px 6px', fontWeight: 600 }}>Not trained</span>
              )}
            </div>
            <div style={{ fontSize: 11, color: '#64748B', marginTop: 3 }}>{isAvailable ? m.description : 'Run model training from the Admin panel to enable this model.'}</div>
          </button>
        );
      })}
    </div>
  );
};

const Analyse: React.FC = () => {
  const [textInput, setTextInput] = useState('');
  const [selectedModels, setSelectedModels] = useState<string[]>(['all']);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [documentReport, setDocumentReport] = useState<AnalysisResult | null>(null);
  const [showPerModel, setShowPerModel] = useState(false);

  const uploadMutation = useUploadDocument();
  const analyzeMutation = useAnalyzeText();
  const { data: history, isLoading: historyLoading } = useUploadHistory();
  const { data: availableModels = [] } = useAvailableModels();

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setSelectedFile(acceptedFiles[0]);
      setDocumentReport(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024,
  });

  const handleDocumentAnalysis = async () => {
    if (!selectedFile) return;
    try {
      uploadMutation.reset();
      const trainedIds = new Set(availableModels.filter((m) => m.available !== 'false').map((m) => m.id));
      const models = selectedModels.includes('all') ? [] : selectedModels.filter((id) => trainedIds.has(id));
      const response = await uploadMutation.mutateAsync({ file: selectedFile, models });
      const result = await detectionService.getAnalysisResult(response.analysis_id);
      setDocumentReport(result);
    } catch {
      // error toast is shown by the mutation's onError callback
    }
  };

  const handleTextAnalysis = async () => {
    if (textInput.trim().length < 10) return;
    const trainedIds = new Set(availableModels.filter((m) => m.available !== 'false').map((m) => m.id));
    const models = selectedModels.includes('all') ? undefined : selectedModels.filter((id) => trainedIds.has(id));
    const result = await analyzeMutation.mutateAsync({ text: textInput, model: 'distilbert', models });
    setAnalysisResult(result);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Model Selection */}
      {availableModels.length > 0 && (
        <div style={{ background: '#FFFFFF', borderRadius: 12, border: '1px solid #E2E8F0', padding: 24 }}>
          <h2 style={{ fontSize: 17, fontWeight: 700, color: '#1E293B', marginBottom: 6 }}>Select ML Models</h2>
          <p style={{ fontSize: 13, color: '#64748B', marginBottom: 16 }}>
            Select one or more models to scan with. Scores are averaged with equal weighting.
          </p>
          <ModelSelector models={availableModels} selected={selectedModels} onChange={setSelectedModels} />
          {selectedModels.length > 1 && !selectedModels.includes('all') && (
            <p style={{ marginTop: 10, fontSize: 12, color: '#2563EB' }}>
              Average score will be computed equally across: {selectedModels.join(', ')}
            </p>
          )}
        </div>
      )}

      {/* File Upload */}
      <div style={{ background: '#FFFFFF', borderRadius: 12, border: '1px solid #E2E8F0', padding: 24 }}>
        <h2 style={{ fontSize: 17, fontWeight: 700, color: '#1E293B', marginBottom: 4 }}>Analyse Document</h2>
        <div style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: 8, padding: '10px 14px', marginBottom: 16 }}>
          <p style={{ fontSize: 13, color: '#1D4ED8', margin: 0, fontWeight: 500 }}>
            CSV or Excel files only (.csv, .xlsx, .xls)
          </p>
          <p style={{ fontSize: 12, color: '#3B82F6', margin: '4px 0 0', lineHeight: 1.5 }}>
            The file must contain messages in the <strong>first column</strong>. The first row (header) will be automatically discarded. All other columns are ignored.
          </p>
        </div>

        <div
          {...getRootProps()}
          style={{
            border: `2px dashed ${isDragActive ? '#2563EB' : '#CBD5E1'}`,
            borderRadius: 10,
            padding: 32,
            textAlign: 'center',
            cursor: 'pointer',
            background: isDragActive ? '#EFF6FF' : '#F8FAFC',
            transition: 'all 0.15s',
          }}
        >
          <input {...getInputProps()} />
          {isDragActive ? (
            <p style={{ color: '#2563EB', fontWeight: 600, margin: 0 }}>Drop the file here</p>
          ) : selectedFile ? (
            <div>
              <p style={{ color: '#1D4ED8', fontWeight: 600, margin: 0 }}>{selectedFile.name}</p>
              <p style={{ fontSize: 12, color: '#64748B', marginTop: 4 }}>
                {(selectedFile.size / 1024).toFixed(1)} KB — click or drop to change file
              </p>
            </div>
          ) : (
            <div>
              <p style={{ color: '#475569', margin: '0 0 6px' }}>Drag and drop a CSV or Excel file here, or click to select</p>
              <p style={{ fontSize: 12, color: '#94A3B8', margin: 0 }}>Supported: .csv, .xlsx, .xls (max 50MB)</p>
            </div>
          )}
        </div>

        {selectedFile && (
          <button
            onClick={handleDocumentAnalysis}
            disabled={uploadMutation.isLoading}
            style={{
              marginTop: 12,
              background: '#2563EB',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: 8,
              padding: '10px 24px',
              fontWeight: 600,
              cursor: uploadMutation.isLoading ? 'not-allowed' : 'pointer',
              opacity: uploadMutation.isLoading ? 0.6 : 1,
              fontSize: 14,
            }}
          >
            {uploadMutation.isLoading ? 'Analyzing…' : 'Analyze Document'}
          </button>
        )}

        {documentReport && (
          <div style={{ marginTop: 20 }}>
            {/* Summary */}
            <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 8, padding: 16, marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                <ThreatBadge level={documentReport.threat_level || 'low'} />
                <span style={{ fontSize: 14, color: '#475569' }}>
                  Average Score: <strong style={{ color: '#1E293B' }}>{documentReport.threat_score?.toFixed(4)}</strong>
                </span>
              </div>
              <p style={{ fontSize: 13, color: '#475569', margin: 0 }}>{documentReport.summary}</p>
              {documentReport.model_scores && Object.keys(documentReport.model_scores).length > 0 && (
                <div style={{ marginTop: 10 }}>
                  <p style={{ fontSize: 12, color: '#94A3B8', margin: '0 0 6px' }}>Per-model average scores:</p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                    {Object.entries(documentReport.model_scores).map(([k, v]) => (
                      <span key={k} style={{ background: '#EFF6FF', color: '#2563EB', borderRadius: 6, padding: '3px 10px', fontSize: 12, fontWeight: 500 }}>
                        {k}: {(v as number).toFixed(4)}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Row results table */}
            {documentReport.row_results && documentReport.row_results.length > 0 && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                  <h3 style={{ fontSize: 15, fontWeight: 600, color: '#1E293B', margin: 0 }}>
                    Row-by-Row Results ({documentReport.row_results.length} rows)
                  </h3>
                  <button
                    onClick={() => setShowPerModel(!showPerModel)}
                    style={{
                      background: showPerModel ? '#EFF6FF' : '#F1F5F9',
                      color: showPerModel ? '#2563EB' : '#475569',
                      border: `1px solid ${showPerModel ? '#BFDBFE' : '#E2E8F0'}`,
                      borderRadius: 6,
                      padding: '5px 14px',
                      fontSize: 12,
                      cursor: 'pointer',
                      fontWeight: 500,
                    }}
                  >
                    {showPerModel ? 'Hide' : 'Show'} per-model scores
                  </button>
                </div>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: '#F8FAFC', borderBottom: '2px solid #E2E8F0' }}>
                        <th style={{ padding: '8px 12px', textAlign: 'left', color: '#64748B', fontWeight: 600, whiteSpace: 'nowrap' }}>Row</th>
                        <th style={{ padding: '8px 12px', textAlign: 'left', color: '#64748B', fontWeight: 600 }}>Message</th>
                        <th style={{ padding: '8px 12px', textAlign: 'left', color: '#64748B', fontWeight: 600, whiteSpace: 'nowrap' }}>Level</th>
                        <th style={{ padding: '8px 12px', textAlign: 'left', color: '#64748B', fontWeight: 600, whiteSpace: 'nowrap' }}>Score</th>
                        {showPerModel && documentReport.row_results[0]?.model_scores &&
                          Object.keys(documentReport.row_results[0].model_scores).map((mk) => (
                            <th key={mk} style={{ padding: '8px 12px', textAlign: 'left', color: '#64748B', fontWeight: 600, whiteSpace: 'nowrap' }}>
                              {mk}
                            </th>
                          ))
                        }
                      </tr>
                    </thead>
                    <tbody>
                      {documentReport.row_results.map((row: RowResult) => (
                        <tr key={row.row} style={{ borderBottom: '1px solid #F1F5F9' }}>
                          <td style={{ padding: '8px 12px', color: '#94A3B8', fontFamily: 'monospace' }}>{row.row}</td>
                          <td style={{ padding: '8px 12px', color: '#374151', maxWidth: 400 }}>
                            <span title={row.message}>
                              {row.message.length > 100 ? row.message.slice(0, 100) + '…' : row.message}
                            </span>
                          </td>
                          <td style={{ padding: '8px 12px' }}>
                            <span style={{
                              background: LEVEL_COLOR[row.threat_level] + '18',
                              color: LEVEL_COLOR[row.threat_level] || '#475569',
                              borderRadius: 5,
                              padding: '2px 8px',
                              fontWeight: 600,
                              fontSize: 12,
                              textTransform: 'capitalize',
                            }}>
                              {row.threat_level}
                            </span>
                          </td>
                          <td style={{ padding: '8px 12px', color: '#1E293B', fontFamily: 'monospace' }}>
                            {row.threat_score.toFixed(4)}
                          </td>
                          {showPerModel && row.model_scores &&
                            Object.entries(row.model_scores).map(([mk, mv]) => (
                              <td key={mk} style={{ padding: '8px 12px', color: '#475569', fontFamily: 'monospace' }}>
                                {(mv as number).toFixed(4)}
                              </td>
                            ))
                          }
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Text Analysis */}
      <div style={{ background: '#FFFFFF', borderRadius: 12, border: '1px solid #E2E8F0', padding: 24 }}>
        <h2 style={{ fontSize: 17, fontWeight: 700, color: '#1E293B', marginBottom: 4 }}>Analyze Text</h2>
        {selectedModels.length > 0 && (
          <div style={{ marginBottom: 12, fontSize: 13, color: '#64748B' }}>
            Using: <strong style={{ color: '#2563EB' }}>{selectedModels.join(', ')}</strong>
            {selectedModels.length > 1 && <span style={{ color: '#94A3B8', marginLeft: 6 }}>(equal-weight average)</span>}
          </div>
        )}
        <textarea
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          placeholder="Paste text content here for threat analysis (minimum 10 characters)..."
          style={{
            width: '100%',
            height: 160,
            padding: '10px 14px',
            border: '1px solid #E2E8F0',
            borderRadius: 8,
            background: '#F8FAFC',
            color: '#1E293B',
            fontSize: 14,
            resize: 'vertical',
            outline: 'none',
            fontFamily: 'inherit',
            boxSizing: 'border-box',
          }}
        />
        <button
          onClick={handleTextAnalysis}
          disabled={textInput.trim().length < 10 || analyzeMutation.isLoading}
          style={{
            marginTop: 10,
            background: '#2563EB',
            color: '#FFFFFF',
            border: 'none',
            borderRadius: 8,
            padding: '10px 24px',
            fontWeight: 600,
            cursor: (textInput.trim().length < 10 || analyzeMutation.isLoading) ? 'not-allowed' : 'pointer',
            opacity: (textInput.trim().length < 10 || analyzeMutation.isLoading) ? 0.6 : 1,
            fontSize: 14,
          }}
        >
          {analyzeMutation.isLoading ? 'Analyzing…' : 'Analyze Text'}
        </button>

        {analysisResult && (
          <div style={{ marginTop: 16, background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 8, padding: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
              <ThreatBadge level={analysisResult.threat_level || 'low'} />
              <span style={{ fontSize: 14, color: '#475569' }}>
                Score: <strong style={{ color: '#1E293B' }}>{analysisResult.threat_score?.toFixed(4)}</strong>
              </span>
            </div>
            <p style={{ fontSize: 13, color: '#475569', margin: '0 0 8px' }}>{analysisResult.summary}</p>
            {analysisResult.keywords && analysisResult.keywords.length > 0 && (
              <p style={{ fontSize: 13, color: '#64748B', margin: 0 }}>
                <strong>Keywords:</strong> {analysisResult.keywords.join(', ')}
              </p>
            )}
            {analysisResult.model_scores && Object.keys(analysisResult.model_scores).length > 0 && (
              <div style={{ marginTop: 10 }}>
                <p style={{ fontSize: 12, color: '#94A3B8', margin: '0 0 6px' }}>Per-model scores:</p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {Object.entries(analysisResult.model_scores).map(([k, v]) => (
                    <span key={k} style={{ background: '#EFF6FF', color: '#2563EB', borderRadius: 6, padding: '3px 10px', fontSize: 12, fontWeight: 500 }}>
                      {k}: {(v as number).toFixed(4)}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Upload History */}
      <div style={{ background: '#FFFFFF', borderRadius: 12, border: '1px solid #E2E8F0', padding: 24 }}>
        <h2 style={{ fontSize: 17, fontWeight: 700, color: '#1E293B', marginBottom: 16 }}>Upload History</h2>
        {historyLoading ? (
          <p style={{ color: '#94A3B8' }}>Loading…</p>
        ) : history && history.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#F8FAFC', borderBottom: '2px solid #E2E8F0' }}>
                  {['File', 'Type', 'Size', 'Status', 'Uploaded'].map((h) => (
                    <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: '#64748B', fontWeight: 600 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {history.map((doc) => (
                  <tr key={doc.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                    <td style={{ padding: '8px 12px', color: '#1E293B' }}>{doc.original_filename}</td>
                    <td style={{ padding: '8px 12px', color: '#475569', textTransform: 'uppercase', fontSize: 11 }}>{doc.file_type}</td>
                    <td style={{ padding: '8px 12px', color: '#475569' }}>
                      {doc.file_size ? `${(doc.file_size / 1024).toFixed(1)} KB` : '—'}
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <span style={{
                        padding: '2px 8px',
                        borderRadius: 5,
                        fontSize: 11,
                        fontWeight: 600,
                        background: doc.status === 'completed' ? '#DCFCE7' : doc.status === 'processing' ? '#FEF9C3' : doc.status === 'failed' ? '#FEE2E2' : '#F1F5F9',
                        color: doc.status === 'completed' ? '#16A34A' : doc.status === 'processing' ? '#CA8A04' : doc.status === 'failed' ? '#DC2626' : '#475569',
                      }}>
                        {doc.status}
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px', color: '#94A3B8' }}>{formatDate(doc.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p style={{ color: '#94A3B8' }}>No documents uploaded yet.</p>
        )}
      </div>
    </div>
  );
};

export default Analyse;

