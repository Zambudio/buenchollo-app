import { apiClient } from "./client";

export interface Notification {
  id: string;
  user_id: string;
  type: string;
  title: string;
  body: string | null;
  link_url: string | null;
  deal_id: string | null;
  alert_id: string | null;
  is_read: boolean;
  created_at: string;
}

export const notificationsApi = {
  list: (): Promise<Notification[]> => apiClient.get<Notification[]>("/notifications"),

  unreadCount: (): Promise<{ count: number }> =>
    apiClient.get<{ count: number }>("/notifications/unread-count"),

  markRead: (): Promise<void> => apiClient.post<void>("/notifications/mark-read", {}),
};
