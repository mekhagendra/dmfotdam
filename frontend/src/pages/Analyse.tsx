import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useUploadDocument, useAnalyzeText, useUploadHistory } from '../hooks/useDetection';
import { AnalysisResult, detectionService } from '../services/detection.service';
import ThreatBadge from '../components/ThreatBadge';
import { formatDate } from '../utils/formatDate';

const Analyse: React.FC = () => {
  const [textInput, setTextInput] = useState('');
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [documentReport, setDocumentReport] = useState<AnalysisResult | null>(null);
  const uploadMutation = useUploadDocument();
  const analyzeMutation = useAnalyzeText();
  const { data: history, isLoading: historyLoading } = useUploadHistory();

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        setSelectedFile(acceptedFiles[0]);
        setDocumentReport(null);
      }
    },
    []
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/json': ['.json'],
    },
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024, // 50MB
  });

  const handleDocumentAnalysis = async () => {
    if (!selectedFile) return;
    try {
      uploadMutation.reset();
      const response = await uploadMutation.mutateAsync(selectedFile);
      const result = await detectionService.getAnalysisResult(response.analysis_id);
      setDocumentReport(result);
    } catch {
      // error toast is shown by the mutation's onError callback
    }
  };

  const handleTextAnalysis = async () => {
    if (textInput.trim().length < 10) return;
    const result = await analyzeMutation.mutateAsync(textInput);
    setAnalysisResult(result);
  };

  return (
    <div className="space-y-6">
      {/* File Upload */}
      <div className="bg-panel rounded-lg border border-edge p-6">
        <h2 className="text-xl font-semibold mb-4 text-slate-100">Analyse content</h2>
        <p className="text-sm text-slate-500 mb-4">Upload a file or paste text for threat analysis</p>
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            isDragActive ? 'border-primary-500 bg-primary-500/10' : 'border-slate-600 hover:border-primary-400'
          }`}
        >
          <input {...getInputProps()} />
          {uploadMutation.isLoading ? (
            <p className="text-slate-500">Uploading and analyzing...</p>
          ) : isDragActive ? (
            <p className="text-primary-600 font-medium">Drop the file here</p>
          ) : selectedFile ? (
            <div>
              <p className="text-primary-700 font-medium">{selectedFile.name}</p>
              <p className="text-sm text-slate-500 mt-1">
                {(selectedFile.size / 1024).toFixed(1)} KB — click or drop to change file
              </p>
            </div>
          ) : (
            <div>
              <p className="text-slate-400 mb-2">Drag and drop a file here, or click to select</p>
              <p className="text-sm text-slate-500">Supported: PDF, DOCX, TXT, CSV, Excel, JSON (max 50MB)</p>
            </div>
          )}
        </div>

        {selectedFile && (
          <button
            onClick={handleDocumentAnalysis}
            disabled={uploadMutation.isLoading}
            className="mt-3 bg-primary-600 text-white py-2 px-6 rounded-md hover:bg-primary-700 disabled:opacity-50 font-medium"
          >
            {uploadMutation.isLoading ? 'Analyzing...' : 'Analyze'}
          </button>
        )}

        {documentReport && (
          <div className="mt-4 p-4 bg-panel-alt border border-edge rounded-md space-y-2">
            <div className="flex items-center gap-3">
              <span className="font-medium text-slate-200">Threat Level:</span>
              <ThreatBadge level={documentReport.threat_level || 'low'} />
              <span className="text-sm text-slate-400">
                Score: {documentReport.threat_score?.toFixed(4)}
              </span>
            </div>
            <p className="text-sm text-slate-300">{documentReport.summary}</p>
            {documentReport.keywords && documentReport.keywords.length > 0 && (
              <div>
                <span className="text-sm font-medium text-slate-300">Keywords: </span>
                <span className="text-sm text-slate-400">{documentReport.keywords.join(', ')}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Text Analysis */}
      <div className="bg-panel rounded-lg border border-edge p-6">
        <h2 className="text-xl font-semibold mb-4 text-slate-100">Analyze Text</h2>
        <textarea
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          placeholder="Paste text content here for threat analysis (minimum 10 characters)..."
          className="w-full h-40 px-3 py-2 border border-slate-600 rounded-md bg-panel focus:outline-none focus:ring-2 focus:ring-primary-500 resize-y text-slate-200 placeholder-slate-500"
        />
        <button
          onClick={handleTextAnalysis}
          disabled={textInput.trim().length < 10 || analyzeMutation.isLoading}
          className="mt-3 bg-primary-600 text-white py-2 px-6 rounded-md hover:bg-primary-700 disabled:opacity-50 font-medium"
        >
          {analyzeMutation.isLoading ? 'Analyzing...' : 'Analyze Text'}
        </button>

        {analysisResult && (
          <div className="mt-4 p-4 bg-panel-alt border border-edge rounded-md space-y-2">
            <div className="flex items-center gap-3">
              <span className="font-medium text-slate-200">Threat Level:</span>
              <ThreatBadge level={analysisResult.threat_level || 'low'} />
              <span className="text-sm text-slate-400">
                Score: {analysisResult.threat_score?.toFixed(4)}
              </span>
            </div>
            <p className="text-sm text-slate-300">{analysisResult.summary}</p>
            {analysisResult.keywords && analysisResult.keywords.length > 0 && (
              <div>
                <span className="text-sm font-medium text-slate-300">Keywords: </span>
                <span className="text-sm text-slate-400">{analysisResult.keywords.join(', ')}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Upload History */}
      <div className="bg-panel rounded-lg border border-edge p-6">
        <h2 className="text-xl font-semibold mb-4 text-slate-100">Upload History</h2>
        {historyLoading ? (
          <p className="text-slate-500">Loading...</p>
        ) : history && history.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-edge text-left">
                  <th className="pb-2 font-medium text-slate-400">File</th>
                  <th className="pb-2 font-medium text-slate-400">Type</th>
                  <th className="pb-2 font-medium text-slate-400">Size</th>
                  <th className="pb-2 font-medium text-slate-400">Status</th>
                  <th className="pb-2 font-medium text-slate-400">Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {history.map((doc) => (
                  <tr key={doc.id} className="border-b border-edge">
                    <td className="py-2 text-slate-200">{doc.original_filename}</td>
                    <td className="py-2 uppercase text-slate-300">{doc.file_type}</td>
                    <td className="py-2 text-slate-300">
                      {doc.file_size ? `${(doc.file_size / 1024).toFixed(1)} KB` : '-'}
                    </td>
                    <td className="py-2">
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-medium ${
                          doc.status === 'completed'
                            ? 'bg-green-500/15 text-green-400'
                            : doc.status === 'processing'
                            ? 'bg-yellow-500/15 text-yellow-400'
                            : doc.status === 'failed'
                            ? 'bg-red-500/15 text-red-400'
                            : 'bg-slate-700/50 text-slate-400'
                        }`}
                      >
                        {doc.status}
                      </span>
                    </td>
                    <td className="py-2 text-slate-500">
                      {formatDate(doc.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-slate-500">No documents uploaded yet.</p>
        )}
      </div>
    </div>
  );
};

export default Analyse;
