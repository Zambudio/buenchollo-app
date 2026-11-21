import { Link } from "@tanstack/react-router";
import { ArrowRight, BookOpen, Flame } from "lucide-react";
import type { BlogPostCard } from "@/services/api/blog";
import type { DealCardData } from "@/features/deals/components/DealCard";
import { calculateDiscount, formatPrice } from "@/lib/format";

const NEW_MS = 24 * 60 * 60 * 1000;

/**
 * Columna lateral de la portada.
 * - «Top de la semana»: los activos con más descuento de los últimos 7 días
 *   (el mismo ranking que el resumen de los domingos). Se calcula en cada
 *   visita, así que entra lo nuevo y cambia de orden solo. «Nuevo» marca lo
 *   dado de alta en las últimas 24 h (no un chollo antiguo reactivado); `now`
 *   es la hora del loader, la misma en el servidor y en el navegador.
 * - Sustituye a «Más populares», que ordenaba por votos (todos a 0).
 */
export function HomeSidebar({
  weeklyTop,
  posts,
  now,
}: {
  weeklyTop: DealCardData[];
  posts: BlogPostCard[];
  now: number;
}) {
  return (
    <aside className="home-sidebar" aria-label="Más por descubrir">
      {weeklyTop.length > 0 && (
        <section className="sidebar-panel" aria-labelledby="weekly-top-heading">
          <h2 id="weekly-top-heading">
            <Flame size={19} aria-hidden="true" /> Top de la semana
          </h2>
          <ol className="weekly-top">
            {weeklyTop.map((deal, index) => {
              const discount =
                deal.discount_percentage ??
                calculateDiscount(deal.current_price, deal.previous_price);
              const isNew = now - new Date(deal.created_at ?? deal.published_at).getTime() < NEW_MS;
              return (
                <li key={deal.id}>
                  <Link to="/chollo/$slug" params={{ slug: deal.slug }}>
                    <span className="weekly-top-rank" aria-hidden="true">
                      {index + 1}
                    </span>
                    {deal.image_url && (
                      <img src={deal.image_url} alt="" loading="lazy" width="56" height="56" />
                    )}
                    <span className="weekly-top-info">
                      <span className="weekly-top-title">{deal.title}</span>
                      <span className="weekly-top-price">
                        <strong>{formatPrice(deal.current_price)}</strong>
                        {discount != null && discount > 0 && (
                          <span className="weekly-top-discount">-{discount}%</span>
                        )}
                        {isNew && <span className="weekly-top-new">Nuevo</span>}
                      </span>
                    </span>
                  </Link>
                </li>
              );
            })}
          </ol>
          <Link className="sidebar-more" to="/explorar" search={{ sort: "discount" }}>
            Ver más chollos <ArrowRight size={15} />
          </Link>
        </section>
      )}
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
