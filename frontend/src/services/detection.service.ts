import api from './api';

export interface MLModel {
  id: string;
  name: string;
  type: string;
  description: string;
  available?: string; // 'true' | 'false' — false means not yet trained
}

export interface RowResult {
  row: number;
  message: string;
  threat_score: number;
  threat_level: string;
  model_scores?: Record<string, number>;
}

export interface AnalysisResult {
  id: string;
  analysis_type: string;
  status: string;
  threat_score: number | null;
  threat_level: string | null;
  summary: string | null;
  details: Record<string, unknown> | null;
  keywords: string[] | null;
  sentiment: string | null;
  language: string | null;
  source_url?: string | null;
  explanation?: Record<string, unknown> | null;
  row_results?: RowResult[] | null;
  model_scores?: Record<string, number> | null;
  created_at: string;
  completed_at: string | null;
}

export interface DocumentInfo {
  id: string;
  filename: string;
  original_filename: string;
  file_type: string;
  file_size: number | null;
  status: string;
  created_at: string;
}

export interface UploadResponse {
  document: DocumentInfo;
  analysis_id: string;
  message: string;
}

export interface DashboardMetrics {
  total_analyses: number;
  total_alerts: number;
  critical_alerts: number;
  high_alerts: number;
  active_sources: number;
  avg_threat_score: number;
  // New fields
  medium_alerts: number;
  low_alerts: number;
  category_breakdown: Record<string, number>;
  threat_trend_24h: number | null;
  analyses_today: number;
  source_breakdown: Record<string, number>;
  active_model: string | null;
  model_f1: number | null;
}

export interface AlertInfo {
  id: string;
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
  id: string;
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
  async uploadDocument(file: File, models?: string[]): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const params = models && models.length > 0 ? `?models=${models.join(',')}` : '';
    const response = await api.post<UploadResponse>(`/upload/document${params}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  async getUploadHistory(): Promise<DocumentInfo[]> {
    const response = await api.get<DocumentInfo[]>('/upload/history');
    return response.data;
  },

  async analyzeText(text: string, model: string = 'distilbert', models?: string[]): Promise<AnalysisResult> {
    const payload: Record<string, unknown> = { text, model };
    if (models && models.length > 0) payload.models = models;
    const response = await api.post<AnalysisResult>('/detection/analyze-text', payload);
    return response.data;
  },

  async trainModels(): Promise<{ job_id: string; status: string; message: string }> {
    const response = await api.post<{ job_id: string; status: string; message: string }>('/users/train-models');
    return response.data;
  },

  async getTrainingStatus(jobId: string): Promise<Record<string, unknown>> {
    const response = await api.get<Record<string, unknown>>(`/users/train-status/${jobId}`);
    return response.data;
  },

  async getAvailableModels(): Promise<MLModel[]> {
    const response = await api.get<MLModel[]>('/detection/models');
    return response.data;
  },

  async getAnalysisResult(id: string): Promise<AnalysisResult> {
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

  async deleteSource(id: string): Promise<void> {
    await api.delete(`/monitoring/sources/${id}`);
  },

  async markAlertRead(id: string): Promise<void> {
    await api.patch(`/monitoring/alerts/${id}/read`);
  },

  async resolveAlert(id: string): Promise<void> {
    await api.patch(`/monitoring/alerts/${id}/resolve`);
  },

  async runScanNow(): Promise<Record<string, unknown>> {
    const response = await api.post('/monitoring/scan/run');
    return response.data;
  },

  async getUnreadAlertCount(): Promise<number> {
    const response = await api.get<AlertInfo[]>('/monitoring/alerts');
    return response.data.filter(a => !a.is_read && !a.is_resolved).length;
  },
};
