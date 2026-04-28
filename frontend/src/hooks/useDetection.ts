import { useQuery, useMutation, useQueryClient } from 'react-query';
import { detectionService } from '../services/detection.service';
import { toast } from 'react-toastify';

export function useDashboardMetrics() {
  return useQuery('dashboardMetrics', detectionService.getDashboardMetrics, {
    refetchInterval: 30000,
  });
}

export function useAlerts() {
  return useQuery('alerts', detectionService.getAlerts, {
    refetchInterval: 15000,
  });
}

export function useReports() {
  return useQuery('reports', detectionService.getReports);
}

export function useUploadHistory() {
  return useQuery('uploadHistory', detectionService.getUploadHistory);
}

export function useSources() {
  return useQuery('sources', detectionService.getSources);
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation(
    (file: File) => detectionService.uploadDocument(file),
    {
      onSuccess: () => {
        toast.success('Document uploaded and analysis started');
        queryClient.invalidateQueries('uploadHistory');
        queryClient.invalidateQueries('reports');
        queryClient.invalidateQueries('dashboardMetrics');
      },
      onError: () => {
        toast.error('Failed to upload document');
      },
    }
  );
}

export function useAnalyzeText() {
  const queryClient = useQueryClient();
  return useMutation(
    ({ text, model }: { text: string; model?: string }) => 
      detectionService.analyzeText(text, model || 'ensemble'),
    {
      onSuccess: () => {
        toast.success('Text analysis completed');
        queryClient.invalidateQueries('reports');
        queryClient.invalidateQueries('dashboardMetrics');
      },
      onError: () => {
        toast.error('Failed to analyze text');
      },
    }
  );
}

export function useAvailableModels() {
  return useQuery('availableModels', detectionService.getAvailableModels);
}

export function useCreateSource() {
  const queryClient = useQueryClient();
  return useMutation(
    (data: { name: string; url: string; source_type: string; keywords: string[]; check_interval: number }) =>
      detectionService.createSource(data),
    {
      onSuccess: () => {
        toast.success('Monitoring source added');
        queryClient.invalidateQueries('sources');
        queryClient.invalidateQueries('dashboardMetrics');
      },
      onError: () => {
        toast.error('Failed to add source');
      },
    }
  );
}

export function useUnreadAlertCount() {
  return useQuery('unreadAlertCount', detectionService.getUnreadAlertCount, {
    refetchInterval: 15000,
  });
}

export function useDeleteSource() {
  const queryClient = useQueryClient();
  return useMutation(
    (id: string) => detectionService.deleteSource(id),
    {
      onSuccess: () => {
        toast.success('Source removed');
        queryClient.invalidateQueries('sources');
      },
      onError: () => {
        toast.error('Failed to delete source');
      },
    }
  );
}
