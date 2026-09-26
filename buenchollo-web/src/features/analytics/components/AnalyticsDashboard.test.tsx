import { render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";

import type { AnalyticsOverview } from "@/services/api/analytics";
import { AnalyticsDashboard } from "./AnalyticsDashboard";

const overview: AnalyticsOverview = {
  days: 30,
  totals: {
    page_views: 100,
    unique_visitors: 50,
    sessions: 60,
    blog_views: 30,
    telegram_visitors: 25,
    organic_visitors: 20,
    telegram_blog_visitors: 10,
    telegram_to_blog_rate: 40,
  },
  timeseries: [],
  sources: [
    { source: "telegram", views: 50, visitors: 25, sessions: 28, blog_views: 14 },
    { source: "organic", views: 35, visitors: 20, sessions: 21, blog_views: 12 },
  ],
  top_pages: [{ path: "/", views: 45, visitors: 30 }],
  top_articles: [
    {
      id: "post-1",
      title: "Guía de portátiles",
      slug: "guia-portatiles",
      view_count: 80,
      views: 20,
      visitors: 14,
    },
  ],
};

beforeAll(() => {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});

describe("AnalyticsDashboard", () => {
  it("prioriza el recorrido Telegram hacia el blog y separa visitas de visitantes", () => {
    render(<AnalyticsDashboard data={overview} />);

    expect(screen.getByText("Telegram → blog")).toBeInTheDocument();
    expect(screen.getByText("40%")).toBeInTheDocument();
    expect(screen.getByText("100")).toBeInTheDocument();
    expect(screen.getAllByText("50").length).toBeGreaterThan(0);
    expect(screen.getByText("Guía de portátiles")).toBeInTheDocument();
  });
});
