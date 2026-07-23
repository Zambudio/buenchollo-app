import { Link } from "@tanstack/react-router";
import { Clock } from "lucide-react";
import type { BlogPostCard as BlogPostCardData } from "@/services/api/blog";

function formatDate(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function BlogPostCard({ post }: { post: BlogPostCardData }) {
  return (
    <Link
      to="/blog/$slug"
      params={{ slug: post.slug }}
      className="group block border border-surface-700 bg-surface-800/40 hover:border-cyan-glow transition-colors rounded overflow-hidden focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-glow"
    >
      <div className="aspect-video bg-surface-900 overflow-hidden">
        {post.cover_image_url && (
          <img
            src={post.cover_image_url}
            alt={post.cover_image_alt ?? ""}
            loading="lazy"
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        )}
      </div>
      <div className="p-4">
        {post.category && (
          <span className="font-mono text-[10px] uppercase tracking-wide text-cyan-glow">
            {post.category.name}
          </span>
        )}
        <h3 className="font-bold text-base leading-snug mt-1 mb-1.5 group-hover:text-cyan-glow transition-colors">
          {post.title}
        </h3>
        {post.excerpt && (
          <p className="text-sm text-muted-foreground line-clamp-2">{post.excerpt}</p>
        )}
        <div className="flex items-center gap-3 mt-3 text-[11px] font-mono text-muted-foreground">
          {post.published_at && (
            <time dateTime={post.published_at}>{formatDate(post.published_at)}</time>
          )}
          <span className="flex items-center gap-1">
            <Clock className="size-3" /> {post.reading_time_minutes} min
          </span>
        </div>
      </div>
    </Link>
  );
}
