import { useQuery } from "@tanstack/react-query";

import { analyticsApi } from "@/services/api/analytics";

export function useAnalyticsOverview(days: number) {
  return useQuery({
    queryKey: ["admin", "analytics", days] as const,
    queryFn: () => analyticsApi.overview(days),
    staleTime: 60 * 1000,
  });
}
