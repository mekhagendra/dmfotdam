/**
 * useWebSocket — connects to /api/v1/ws/live and dispatches incoming
 * messages to the React Query cache so components auto-update.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { useQueryClient } from 'react-query';
import { DashboardMetrics, AlertInfo } from '../services/detection.service';

const WS_BASE =
  process.env.REACT_APP_WS_URL ||
  `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/api/v1`;
const MAX_BACKOFF_MS = 30_000;

export function useWebSocket(): { connected: boolean } {
  const [connected, setConnected] = useState(false);
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(1_000);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      return;
    }

    const url = `${WS_BASE}/ws/live?token=${encodeURIComponent(token)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      setConnected(true);
      backoffRef.current = 1_000; // reset backoff on success
    };

    ws.onmessage = (event: MessageEvent) => {
      if (!mountedRef.current) return;
      try {
        const msg = JSON.parse(event.data as string) as {
          type: string;
          data: unknown;
        };

        if (msg.type === 'alert') {
          queryClient.setQueryData<AlertInfo[]>('alerts', (old) => {
            const alert = msg.data as AlertInfo;
            const prev = old ?? [];
            return [alert, ...prev];
          });
        }

        if (msg.type === 'metrics') {
          // Only update cache if we don't already have data from the REST endpoint
          const existing = queryClient.getQueryData<DashboardMetrics>('dashboardMetrics');
          if (!existing) {
            queryClient.setQueryData<DashboardMetrics>(
              'dashboardMetrics',
              msg.data as DashboardMetrics,
            );
          } else {
            // Merge: only update fields that WebSocket can provide fresher
            queryClient.setQueryData<DashboardMetrics>('dashboardMetrics', {
              ...existing,
              ...(msg.data as DashboardMetrics),
            });
          }
        }
      } catch {
        // Ignore non-JSON messages
      }
    };

    ws.onerror = () => {
      // Error handling is done in onclose
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      setConnected(false);
      wsRef.current = null;

      // Reconnect with exponential backoff
      const delay = backoffRef.current;
      backoffRef.current = Math.min(delay * 2, MAX_BACKOFF_MS);
      setTimeout(() => {
        if (mountedRef.current) {
          connect();
        }
      }, delay);
    };
  }, [queryClient]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { connected };
}
