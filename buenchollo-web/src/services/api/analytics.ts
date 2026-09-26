import { apiClient } from "./client";
import type { AnalyticsSource, Attribution } from "@/features/analytics/lib/tracking";

export interface TrackPageViewPayload {
  visitor_id: string;
  session_id: string;
  path: string;
  source: AnalyticsSource;
  source_detail: string;
  medium: string;
  campaign: string | null;
  referrer_host: string | null;
}

export interface TrackPageViewResponse {
  accepted: boolean;
  blog_view_count: number | null;
}

export interface AnalyticsTotals {
  page_views: number;
  unique_visitors: number;
  sessions: number;
  blog_views: number;
  telegram_visitors: number;
  organic_visitors: number;
  telegram_blog_visitors: number;
  telegram_to_blog_rate: number;
}

export interface AnalyticsDay {
  date: string;
  views: number;
  visitors: number;
}

export interface AnalyticsSourceRow {
  source: AnalyticsSource;
  views: number;
  visitors: number;
  sessions: number;
  blog_views: number;
}

export interface AnalyticsPageRow {
  path: string;
  views: number;
  visitors: number;
}

export interface AnalyticsArticleRow {
  id: string;
  title: string;
  slug: string;
  view_count: number;
  views: number;
  visitors: number;
}

export interface AnalyticsOverview {
  days: number;
  totals: AnalyticsTotals;
  timeseries: AnalyticsDay[];
  sources: AnalyticsSourceRow[];
  top_pages: AnalyticsPageRow[];
  top_articles: AnalyticsArticleRow[];
}

export function attributionPayload(attribution: Attribution) {
  return {
    source: attribution.source,
    source_detail: attribution.sourceDetail,
    medium: attribution.medium,
    campaign: attribution.campaign,
    referrer_host: attribution.referrerHost,
  };
}

export const analyticsApi = {
  track: (payload: TrackPageViewPayload): Promise<TrackPageViewResponse> =>
    apiClient.post<TrackPageViewResponse>("/analytics/events", payload),
  overview: (days: number): Promise<AnalyticsOverview> =>
    apiClient.get<AnalyticsOverview>(`/analytics/admin/overview?days=${days}`),
};
