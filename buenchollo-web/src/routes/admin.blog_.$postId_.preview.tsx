import { createFileRoute, Link } from "@tanstack/react-router";
import { AlertTriangle, ArrowLeft } from "lucide-react";
import { useAdminPost } from "@/features/blog/hooks/useBlogAdmin";
import { ContentRenderer } from "@/features/blog/components/public/ContentRenderer";
import { AffiliateDisclosure } from "@/features/blog/components/public/AffiliateDisclosure";
import { TableOfContents } from "@/features/blog/components/public/TableOfContents";

export const Route = createFileRoute("/admin/blog_/$postId_/preview")({
  component: AdminBlogPreview,
  head: () => ({ meta: [{ name: "robots", content: "noindex, nofollow" }] }),
});

function AdminBlogPreview() {
  const { postId } = Route.useParams();
  const { data: post, isLoading } = useAdminPost(postId);

  if (isLoading || !post) return <div className="h-96 border border-surface-700 animate-pulse" />;

  return (
    <div>
      <div className="mb-4 border border-amber-500/40 bg-amber-500/10 text-amber-400 px-4 py-2 font-mono text-xs uppercase flex items-center gap-2">
        <AlertTriangle className="size-4" /> Previsualización · no publicado para el público
      </div>
      <Link
        to="/admin/blog/$postId"
        params={{ postId }}
        className="inline-flex items-center gap-1.5 text-xs font-mono uppercase text-muted-foreground hover:text-cyan-glow mb-4"
      >
        <ArrowLeft className="size-3.5" /> Volver al editor
      </Link>

      <article className="max-w-[760px] mx-auto bg-surface-950 border border-surface-700 p-6">
        <header className="mb-6">
          {post.category && (
            <span className="font-mono text-xs uppercase text-cyan-glow">{post.category.name}</span>
          )}
          <h1 className="text-3xl font-bold tracking-tight mt-2 mb-3">{post.title}</h1>
          {post.excerpt && <p className="text-lg text-muted-foreground">{post.excerpt}</p>}
        </header>
        {post.cover_image_url && (
          <img
            src={post.cover_image_url}
            alt={post.cover_image_alt ?? ""}
            className="w-full rounded-lg mb-6"
          />
        )}
        {post.has_affiliate_links && <AffiliateDisclosure />}
        <TableOfContents toc={post.toc} />
        <div className="prose prose-invert prose-cyan max-w-none">
          <ContentRenderer doc={post.content} products={post.products} />
        </div>
      </article>
    </div>
  );
}
