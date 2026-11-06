import { Link } from "@tanstack/react-router";
import { ArrowRight, BookOpen, TrendingUp } from "lucide-react";
import type { BlogPostCard } from "@/services/api/blog";
import type { DealCardData } from "@/features/deals/components/DealCard";
import { formatPrice } from "@/lib/format";

export function HomeSidebar({
  popular,
  posts,
}: {
  popular: DealCardData[];
  posts: BlogPostCard[];
}) {
  return (
    <aside className="home-sidebar" aria-label="Más por descubrir">
      <section className="sidebar-panel">
        <h2>
          <TrendingUp size={19} aria-hidden="true" /> Más populares
        </h2>
        {popular.length ? (
          <ul>
            {popular.map((deal) => (
              <li key={deal.id}>
                <Link to="/chollo/$slug" params={{ slug: deal.slug }}>
                  {deal.image_url && (
                    <img src={deal.image_url} alt="" loading="lazy" width="64" height="64" />
                  )}
                  <span>
                    {deal.title}
                    <strong>{formatPrice(deal.current_price)}</strong>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p>Los chollos destacados aparecerán aquí.</p>
        )}
        <Link className="sidebar-more" to="/explorar">
          Ver todos <ArrowRight size={15} />
        </Link>
      </section>
      <section className="sidebar-panel">
        <h2>
          <BookOpen size={19} aria-hidden="true" /> En el blog
        </h2>
        {posts.length ? (
          <ul>
            {posts.map((post) => (
              <li key={post.id}>
                <Link to="/blog/$slug" params={{ slug: post.slug }}>
                  {post.cover_image_url && (
                    <img
                      className="sidebar-thumb-cover"
                      src={post.cover_image_url}
                      alt=""
                      loading="lazy"
                      width="96"
                      height="64"
                    />
                  )}
                  <span>{post.title}</span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p>Guías y comparativas de tecnología para comprar mejor.</p>
        )}
        <Link className="sidebar-more" to="/blog">
          Leer artículos <ArrowRight size={15} />
        </Link>
      </section>
    </aside>
  );
}
