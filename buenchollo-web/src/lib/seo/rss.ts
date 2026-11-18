/** Feeds RSS 2.0 (chollos y blog). Los leen agregadores, lectores y algunos
 *  asistentes de IA para descubrir contenido nuevo sin rastrear la web entera. */
import { escapeXml } from "@/lib/xml";

export interface RssItem {
  title: string;
  url: string;
  description?: string | null;
  publishedAt?: string | null;
  category?: string | null;
}

export interface RssChannel {
  title: string;
  link: string;
  selfUrl: string;
  description: string;
  items: RssItem[];
}

function rssDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toUTCString();
}

function renderItem(item: RssItem): string {
  const pubDate = rssDate(item.publishedAt);
  return [
    "  <item>",
    `    <title>${escapeXml(item.title)}</title>`,
    `    <link>${escapeXml(item.url)}</link>`,
    `    <guid isPermaLink="true">${escapeXml(item.url)}</guid>`,
    item.description ? `    <description>${escapeXml(item.description)}</description>` : null,
    pubDate ? `    <pubDate>${pubDate}</pubDate>` : null,
    item.category ? `    <category>${escapeXml(item.category)}</category>` : null,
    "  </item>",
  ]
    .filter(Boolean)
    .join("\n");
}

export function renderRss(channel: RssChannel): string {
  return [
    `<?xml version="1.0" encoding="UTF-8"?>`,
    `<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">`,
    "<channel>",
    `  <title>${escapeXml(channel.title)}</title>`,
    `  <link>${escapeXml(channel.link)}</link>`,
    `  <atom:link href="${escapeXml(channel.selfUrl)}" rel="self" type="application/rss+xml" />`,
    `  <description>${escapeXml(channel.description)}</description>`,
    "  <language>es-ES</language>",
    ...channel.items.map(renderItem),
    "</channel>",
    "</rss>",
  ].join("\n");
}

export const RSS_HEADERS = {
  "Content-Type": "application/rss+xml; charset=utf-8",
  "Cache-Control": "public, max-age=1800",
};
