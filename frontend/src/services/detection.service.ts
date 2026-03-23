import api from './api';

export interface AnalysisResult {
  id: number;
  analysis_type: string;
  status: string;
  threat_score: number | null;
  threat_level: string | null;
  summary: string | null;
  details: Record<string, unknown> | null;
  keywords: string[] | null;
  sentiment: string | null;
  language: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface DocumentInfo {
  id: number;
  filename: string;
  original_filename: string;
  file_type: string;
  file_size: number | null;
  status: string;
  created_at: string;
}

export interface UploadResponse {
  document: DocumentInfo;
  analysis_id: number;
  message: string;
}

export interface DashboardMetrics {
  total_analyses: number;
  total_alerts: number;
  critical_alerts: number;
  high_alerts: number;
  active_sources: number;
  avg_threat_score: number;
}

export interface AlertInfo {
  id: number;
  title: string;
  description: string | null;
  threat_level: string;
  threat_score: number;
  source: string | null;
  source_type: string | null;
  is_read: boolean;
  is_resolved: boolean;
  created_at: string;
}

export interface MonitoringSource {
  id: number;
  name: string;
  url: string;
  source_type: string;
  keywords: string[] | null;
  is_active: boolean;
  check_interval: number;
  last_checked: string | null;
  created_at: string;
}

export const detectionService = {
  async uploadDocument(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post<UploadResponse>('/upload/document', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  async getUploadHistory(): Promise<DocumentInfo[]> {
    const response = await api.get<DocumentInfo[]>('/upload/history');
    return response.data;
  },

  async analyzeText(text: string): Promise<AnalysisResult> {
    const response = await api.post<AnalysisResult>('/detection/analyze-text', { text });
    return response.data;
  },

  async getAnalysisResult(id: number): Promise<AnalysisResult> {
    const response = await api.get<AnalysisResult>(`/detection/results/${id}`);
    return response.data;
  },

  async getReports(): Promise<AnalysisResult[]> {
    const response = await api.get<AnalysisResult[]>('/detection/reports');
    return response.data;
  },

  async getDashboardMetrics(): Promise<DashboardMetrics> {
    const response = await api.get<DashboardMetrics>('/monitoring/dashboard/metrics');
    return response.data;
  },

  async getAlerts(): Promise<AlertInfo[]> {
    const response = await api.get<AlertInfo[]>('/monitoring/alerts');
    return response.data;
  },

  async getSources(): Promise<MonitoringSource[]> {
    const response = await api.get<MonitoringSource[]>('/monitoring/sources');
    return response.data;
  },

  async createSource(data: {
    name: string;
    url: string;
    source_type: string;
    keywords: string[];
    check_interval: number;
  }): Promise<MonitoringSource> {
    const response = await api.post<MonitoringSource>('/monitoring/sources', data);
    return response.data;
  },

  async deleteSource(id: number): Promise<void> {
    await api.delete(`/monitoring/sources/${id}`);
  },

  async markAlertRead(id: number): Promise<void> {
    await api.patch(`/monitoring/alerts/${id}/read`);
  },

  async resolveAlert(id: number): Promise<void> {
    await api.patch(`/monitoring/alerts/${id}/resolve`);
  },
};
