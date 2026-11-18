import { TIME_ZONE } from "@/lib/format";
import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Share2, Clock, User } from "lucide-react";
import { Layout } from "@/components/layout/Layout";
import { blogService, type BlogPostDetail } from "@/services/api/blog";
import { useRelatedPosts } from "@/features/blog/hooks/useBlogPublic";
import { ContentRenderer } from "@/features/blog/components/public/ContentRenderer";
import { AffiliateDisclosure } from "@/features/blog/components/public/AffiliateDisclosure";
import { TableOfContents } from "@/features/blog/components/public/TableOfContents";
import { BlogPostCard } from "@/features/blog/components/public/BlogPostCard";
import { BlogComments } from "@/features/blog/components/public/BlogComments";
import { BlogPostVoteControl } from "@/features/blog/components/public/BlogPostVoteControl";
import { BlogViewCount } from "@/features/blog/components/public/BlogViewCount";
import { ShareDialog } from "@/features/deals/components/ShareBox";
import { useAuth } from "@/hooks/useAuth";
import { errorMessage } from "@/lib/errors";
import { ApiError } from "@/services/api/client";
import { pageHead } from "@/lib/seo/head";
import { blogPostSeo } from "@/lib/seo/blog";

function formatDate(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("es-ES", {
    timeZone: TIME_ZONE,
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

export const Route = createFileRoute("/blog_/$slug")({
  component: BlogPostPage,
  loader: async ({ params }) => {
    try {
      return { post: await blogService.getPostBySlug(params.slug) };
    } catch (error) {
      // 404 real para buscadores; otros fallos se propagan como 5xx.
      if (error instanceof ApiError && error.status === 404) throw notFound();
      throw error;
    }
  },
  head: ({ loaderData }) => (loaderData?.post ? pageHead(blogPostSeo(loaderData.post)) : {}),
});

function BlogPostPage() {
  const { slug } = Route.useParams();
  const loaderData = Route.useLoaderData();
  const post = loaderData?.post as BlogPostDetail | null;
  const { data: related } = useRelatedPosts(slug, 3);
  const { user } = useAuth();
  const [votes, setVotes] = useState({ up: post?.votes_up ?? 0, down: post?.votes_down ?? 0 });
  const [myVote, setMyVote] = useState(0);
  const [voting, setVoting] = useState(false);

  useEffect(() => {
    setVotes({ up: post?.votes_up ?? 0, down: post?.votes_down ?? 0 });
  }, [post?.id, post?.votes_up, post?.votes_down]);

  const postId = post?.id;
  useEffect(() => {
    if (!user || !postId) {
      setMyVote(0);
      return;
    }
    let cancelled = false;
    blogService
      .getMyVote(postId)
      .then((v) => {
        if (!cancelled) setMyVote(v);
      })
      .catch(() => {
        /* no crítico */
      });
    return () => {
      cancelled = true;
    };
  }, [user, postId]);

  const handleVote = async (vote: 1 | -1) => {
    if (!user) {
      toast.error("Inicia sesión para votar");
      return;
    }
    if (!post || voting) return;
    setVoting(true);
    try {
      const result = await blogService.vote(post.id, vote);
      setVotes({ up: result.votes_up, down: result.votes_down });
      setMyVote(result.my_vote);
    } catch (e: unknown) {
      toast.error(errorMessage(e, "No se pudo registrar el voto"));
    } finally {
      setVoting(false);
    }
  };

  if (!post) {
    return (
      <Layout>
        <div className="max-w-3xl mx-auto p-8 text-center">
          <h1 className="text-2xl font-bold mb-2">Artículo no encontrado</h1>
          <Link to="/blog" className="text-cyan-glow font-mono text-xs">
            VOLVER AL BLOG
          </Link>
        </div>
      </Layout>
    );
  }

  const isUpdated = post.updated_at && post.published_at && post.updated_at !== post.published_at;

  return (
    <Layout>
      <article className="max-w-[760px] mx-auto px-4 sm:px-6 py-10">
        <nav
          aria-label="Ruta de navegación"
          className="font-mono text-xs text-muted-foreground mb-4"
        >
          <ol className="flex flex-wrap gap-x-1">
            <li>
              <Link to="/" className="hover:text-cyan-glow">
                INICIO
              </Link>{" "}
              /
            </li>
            <li>
              <Link to="/blog" className="hover:text-cyan-glow">
                BLOG
              </Link>
              {post.category && " /"}
            </li>
            {post.category && (
              <li aria-current="page" className="text-foreground">
                {post.category.name.toUpperCase()}
              </li>
            )}
          </ol>
        </nav>

        <header className="mb-6">
          {post.category && (
            <span className="font-mono text-xs uppercase text-cyan-glow">{post.category.name}</span>
          )}
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-2 mb-3 leading-tight">
            {post.title}
          </h1>
          {post.excerpt && <p className="text-lg text-muted-foreground mb-4">{post.excerpt}</p>}
          <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-muted-foreground">
            {post.author?.display_name && (
              <span className="flex items-center gap-1.5">
                <User className="size-3.5" /> {post.author.display_name}
              </span>
            )}
            {post.published_at && (
              <time dateTime={post.published_at}>{formatDate(post.published_at)}</time>
            )}
            {isUpdated && <span>· Actualizado el {formatDate(post.updated_at)}</span>}
            <span className="flex items-center gap-1.5">
              <Clock className="size-3.5" /> {post.reading_time_minutes} min de lectura
            </span>
            <ShareDialog
              url={`/blog/${post.slug}`}
              title={post.title}
              trigger={
                <button
                  type="button"
                  aria-label="Compartir artículo"
                  className="flex items-center gap-1.5 hover:text-cyan-glow"
                >
                  <Share2 className="size-3.5" /> Compartir
                </button>
              }
            />
          </div>
        </header>

        {post.cover_image_url && (
          <img
            src={post.cover_image_url}
            alt={post.cover_image_alt ?? ""}
            className="w-full rounded-lg mb-6"
            loading="eager"
          />
        )}

        {post.has_affiliate_links && <AffiliateDisclosure />}

        <TableOfContents toc={post.toc} />

        <div className="prose dark:prose-invert prose-cyan max-w-none prose-headings:scroll-mt-20 prose-img:rounded-lg">
          <ContentRenderer doc={post.content} products={post.products} />
        </div>

        <div className="not-prose mt-10 pt-6 border-t border-surface-700 flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3 flex-wrap">
            <BlogViewCount count={post.view_count} />
            <span className="text-sm text-muted-foreground">¿Te ha sido útil este artículo?</span>
            <BlogPostVoteControl
              votesUp={votes.up}
              votesDown={votes.down}
              myVote={myVote}
              disabled={voting}
              onVote={handleVote}
            />
          </div>
          <ShareDialog
            url={`/blog/${post.slug}`}
            title={post.title}
            trigger={
              <button
                type="button"
                className="inline-flex items-center gap-2 border border-surface-700 hover:border-cyan-glow hover:text-cyan-glow px-4 py-2 font-mono text-xs uppercase transition-colors"
              >
                <Share2 className="size-4" /> Compartir en redes
              </button>
            }
          />
        </div>

        {related && related.length > 0 && (
          <section className="mt-10 not-prose">
            <h2 className="font-bold text-lg mb-4">Artículos relacionados</h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {related.map((r) => (
                <BlogPostCard key={r.id} post={r} />
              ))}
            </div>
          </section>
        )}

        <BlogComments postId={post.id} />
      </article>
    </Layout>
  );
}
