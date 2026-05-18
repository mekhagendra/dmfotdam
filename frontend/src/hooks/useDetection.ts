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

export function useSourceDailyTrends(days: number) {
  return useQuery(['sourceDailyTrends', days], () => detectionService.getSourceDailyTrends(days), {
    refetchInterval: 60000,
  });
}

export function useCollectedItems(days: number, limit: number = 200) {
  return useQuery(['collectedItems', days, limit], () => detectionService.getCollectedItems(days, limit), {
    refetchInterval: 30000,
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation(
    ({ file, models }: { file: File; models?: string[] }) => detectionService.uploadDocument(file, models),
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
    ({ text, model, models }: { text: string; model?: string; models?: string[] }) => 
      detectionService.analyzeText(text, model || 'distilbert', models),
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

export function useTrainModels() {
  const queryClient = useQueryClient();
  return useMutation(
    () => detectionService.trainModels(),
    {
      onSuccess: () => {
        toast.info('Model training started');
        queryClient.invalidateQueries('availableModels');
      },
      onError: () => {
        toast.error('Failed to start model training');
      },
    }
  );
}

export function useTrainingStatus(jobId: string | null) {
  return useQuery(
    ['trainingStatus', jobId],
    () => detectionService.getTrainingStatus(jobId!),
    {
      enabled: !!jobId,
      refetchInterval: (data: any) =>
        data && (data.status === 'completed' || data.status === 'failed') ? false : 3000,
    }
  );
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

export function useRunScanNow() {
  const queryClient = useQueryClient();
  return useMutation(() => detectionService.runScanNow(), {
    onSuccess: (data: any) => {
      const polled = typeof data?.sources_polled === 'number' ? data.sources_polled : null;
      const newItems = typeof data?.results === 'object'
        ? (data.results as any[]).reduce((s: number, r: any) => s + (typeof r.new === 'number' ? r.new : 0), 0)
        : null;
      const msg = polled !== null
        ? `Scan complete — ${polled} source(s) polled, ${newItems ?? 0} new item(s)`
        : 'Scan completed';
      toast.success(msg);
      // Invalidate then immediately refetch so the UI updates right away.
      queryClient.invalidateQueries('alerts');
      queryClient.invalidateQueries('collectedItems');
      queryClient.invalidateQueries('dashboardMetrics');
      queryClient.invalidateQueries('sources');
      queryClient.refetchQueries('alerts');
      queryClient.refetchQueries('collectedItems');
    },
    onError: () => {
      toast.error('Failed to run scan');
    },
  });
}

export function useResetScannedData() {
  const queryClient = useQueryClient();
  return useMutation(() => detectionService.resetScannedData(), {
    onSuccess: (data: any) => {
      const itemsDeleted = typeof data?.items_deleted === 'number' ? data.items_deleted : 0;
      const alertsDeleted = typeof data?.alerts_deleted === 'number' ? data.alerts_deleted : 0;
      toast.success(`Scanned data reset: ${itemsDeleted} items and ${alertsDeleted} alerts removed`);
      queryClient.invalidateQueries('alerts');
      queryClient.invalidateQueries('collectedItems');
      queryClient.invalidateQueries('dashboardMetrics');
      queryClient.invalidateQueries('sourceDailyTrends');
    },
    onError: () => {
      toast.error('Failed to reset scanned data');
    },
  });
}
