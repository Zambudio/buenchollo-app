import { Link } from "@tanstack/react-router";
import { ArrowRight, BookOpen } from "lucide-react";
import type { BlogPostCard } from "@/services/api/blog";

/** Columna lateral de la portada. Sin «Más populares»: ordenaba por votos y,
 *  con la comunidad arrancando, todos estaban a 0. */
export function HomeSidebar({ posts }: { posts: BlogPostCard[] }) {
  return (
    <aside className="home-sidebar" aria-label="Más por descubrir">
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
