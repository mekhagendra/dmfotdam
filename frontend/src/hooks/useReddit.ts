import { useQuery, useMutation, useQueryClient } from 'react-query';
import { redditService, RedditPost } from '../services/reddit.service';
import { toast } from 'react-toastify';

export function useRedditStatus() {
  return useQuery('redditStatus', redditService.getStatus, {
    refetchInterval: 60000,
  });
}

export function useRedditTrends(days = 30) {
  return useQuery(['redditTrends', days], () => redditService.getTrends(days), {
    refetchInterval: 300000,
  });
}

export function useSubredditStats(days = 30) {
  return useQuery(['subredditStats', days], () => redditService.getSubredditStats(days), {
    refetchInterval: 300000,
  });
}

export function useFlaggedPosts(params?: {
  threat_level?: string;
  subreddit?: string;
  days?: number;
  limit?: number;
  offset?: number;
}) {
  return useQuery(['flaggedPosts', params], () => redditService.getFlaggedPosts(params), {
    refetchInterval: 60000,
  });
}

export function useRedditPostDetail(id: number | null) {
  return useQuery(['redditPost', id], () => redditService.getPostDetail(id!), {
    enabled: id !== null,
  });
}

export function useTriggerScan() {
  const queryClient = useQueryClient();
  return useMutation(
    (params?: { subreddits?: string[]; limit?: number; threat_threshold?: number }) =>
      redditService.triggerScan(params),
    {
      onSuccess: (data) => {
        toast.success(`Scan complete: ${data.total_flagged} threats found from ${data.total_scanned} posts`);
        queryClient.invalidateQueries('flaggedPosts');
        queryClient.invalidateQueries('redditTrends');
        queryClient.invalidateQueries('subredditStats');
        queryClient.invalidateQueries('redditStatus');
      },
      onError: () => {
        toast.error('Reddit scan failed');
      },
    }
  );
}

export function useSearchReddit() {
  return useMutation(
    (params: { query: string; subreddits?: string[]; limit?: number; time_filter?: string }) =>
      redditService.searchReddit(params),
    {
      onError: () => {
        toast.error('Reddit search failed');
      },
    }
  );
}

export function useMarkReviewed() {
  const queryClient = useQueryClient();
  return useMutation(
    (id: number) => redditService.markPostReviewed(id),
    {
      onSuccess: () => {
        toast.success('Post marked as reviewed');
        queryClient.invalidateQueries('flaggedPosts');
      },
      onError: () => {
        toast.error('Failed to mark as reviewed');
      },
    }
  );
}
