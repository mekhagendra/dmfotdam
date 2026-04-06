import api from './api';

export interface RedditPost {
  id: number;
  reddit_id: string;
  subreddit: string;
  title: string;
  text: string;
  author: string;
  url: string;
  score: number;
  num_comments: number;
  threat_score: number;
  threat_level: string;
  analysis_details: Record<string, unknown> | null;
  posted_at: string | null;
  scanned_at: string | null;
  is_reviewed: boolean;
}

export interface TrendDataPoint {
  date: string;
  total_posts: number;
  avg_threat_score: number;
  max_threat_score: number;
  high_threat_count: number;
}

export interface SubredditStats {
  subreddit: string;
  total_posts: number;
  avg_threat_score: number;
  max_threat_score: number;
  high_threat_count: number;
}

export interface ScanResult {
  status: string;
  scan_time: string | null;
  total_scanned: number;
  total_flagged: number;
  new_posts_stored: number;
  new_alerts_generated: number;
  reason: string | null;
}

export interface RedditStatus {
  available: boolean;
  message: string;
  default_subreddits: string[];
  total_stored_posts: number;
  last_scan_time: string | null;
}

export interface SearchResult {
  query: string;
  total_results: number;
  posts: Array<{
    reddit_id: string;
    subreddit: string;
    title: string;
    text: string;
    author: string;
    url: string;
    score: number;
    num_comments: number;
    threat_score: number;
    threat_level: string;
    created_utc: string;
    analysis: Record<string, unknown> | null;
  }>;
}

export const redditService = {
  async getStatus(): Promise<RedditStatus> {
    const response = await api.get<RedditStatus>('/reddit/status');
    return response.data;
  },

  async triggerScan(params?: {
    subreddits?: string[];
    limit?: number;
    threat_threshold?: number;
  }): Promise<ScanResult> {
    const response = await api.post<ScanResult>('/reddit/scan', params || {});
    return response.data;
  },

  async searchReddit(params: {
    query: string;
    subreddits?: string[];
    limit?: number;
    time_filter?: string;
  }): Promise<SearchResult> {
    const response = await api.post<SearchResult>('/reddit/search', params);
    return response.data;
  },

  async getFlaggedPosts(params?: {
    threat_level?: string;
    subreddit?: string;
    days?: number;
    limit?: number;
    offset?: number;
  }): Promise<RedditPost[]> {
    const response = await api.get<RedditPost[]>('/reddit/posts', { params });
    return response.data;
  },

  async getPostDetail(id: number): Promise<RedditPost> {
    const response = await api.get<RedditPost>(`/reddit/posts/${id}`);
    return response.data;
  },

  async markPostReviewed(id: number): Promise<void> {
    await api.patch(`/reddit/posts/${id}/review`);
  },

  async getTrends(days?: number): Promise<TrendDataPoint[]> {
    const response = await api.get<TrendDataPoint[]>('/reddit/trends', {
      params: days ? { days } : undefined,
    });
    return response.data;
  },

  async getSubredditStats(days?: number): Promise<SubredditStats[]> {
    const response = await api.get<SubredditStats[]>('/reddit/subreddits', {
      params: days ? { days } : undefined,
    });
    return response.data;
  },
};
