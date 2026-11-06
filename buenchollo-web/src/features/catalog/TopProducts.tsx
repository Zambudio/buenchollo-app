import { Link } from "@tanstack/react-router";
import { ArrowUpRight, Crown, ThumbsUp } from "lucide-react";
import { useEffect, useState } from "react";
import { formatPrice } from "@/lib/format";
import { catalogService, type TopProduct } from "@/services/api/catalog";
import { onProductVoteChange, useProductVote } from "./productVotes";

function TopVoteButton({ product }: { product: TopProduct }) {
  const { isLoggedIn, voted, pending, toggle } = useProductVote(product.id);
  const content = (
    <>
      <ThumbsUp size={15} aria-hidden="true" /> <span>{product.vote_count}</span>
    </>
  );
  if (!isLoggedIn) {
    return (
      <Link
        className="vote-chip top-vote"
        to="/login"
        aria-label={`Accede para votar por ${product.title}`}
      >
        {content}
      </Link>
    );
  }
  return (
    <button
      className={`vote-chip top-vote ${voted ? "is-voted" : ""}`}
      type="button"
      aria-label={`${voted ? "Retirar voto a" : "Votar por"} ${product.title}`}
      aria-pressed={voted}
      disabled={pending}
      onClick={() => void toggle()}
    >
      {content}
    </button>
  );
}

function TopProductCard({ product, podium }: { product: TopProduct; podium: boolean }) {
  return (
    <article className={podium ? `top-podium-card top-place-${product.position}` : "top-list-card"}>
      <span className="top-position" aria-label={`Puesto ${product.position}`}>
        {product.position === 1 && <Crown aria-hidden="true" size={15} />}
        {product.position}
      </span>
      {product.image_url ? (
        <img
          className="top-product-image"
          src={product.image_url}
          alt=""
          loading="lazy"
          width="112"
          height="112"
        />
      ) : (
        <span className="top-product-image top-no-image" aria-hidden="true">
          BC
        </span>
      )}
      <div className="top-product-info">
        <h3>
          {product.deal_slug ? (
            <Link to="/chollo/$slug" params={{ slug: product.deal_slug }}>
              {product.title}
            </Link>
          ) : (
            product.title
          )}
        </h3>
        <p>
          {product.current_price != null ? (
            <strong>{formatPrice(product.current_price)}</strong>
          ) : (
            "Sin oferta activa"
          )}
          {product.deal_slug && (
            <Link
              to="/chollo/$slug"
              params={{ slug: product.deal_slug }}
              aria-label={`Ver ${product.title}`}
            >
              <ArrowUpRight size={15} />
            </Link>
          )}
        </p>
      </div>
      <TopVoteButton product={product} />
    </article>
  );
}

export function TopProducts({
  slug,
  initialProducts,
}: {
  slug: string;
  initialProducts: TopProduct[];
}) {
  const [products, setProducts] = useState(initialProducts);
  const [error, setError] = useState("");

  useEffect(() => {
    setProducts(initialProducts);
  }, [initialProducts]);

  // Cualquier voto (aquí o en una tarjeta) mueve el contador al instante y se
  // confirma recargando el ranking, que puede cambiar de orden.
  useEffect(
    () =>
      onProductVoteChange(({ productId, voted }) => {
        setError("");
        setProducts((previous) =>
          previous.map((product) =>
            product.id === productId
              ? { ...product, vote_count: product.vote_count + (voted ? 1 : -1) }
              : product,
          ),
        );
        catalogService
          .top(slug)
          .then(setProducts)
          .catch(() => {
            setError(
              "Voto guardado. No hemos podido actualizar las posiciones; recarga la página.",
            );
          });
      }),
    [slug],
  );

  return (
    <section className="top-products" aria-labelledby="top-products-heading">
      <div className="top-section-heading">
        <div>
          <span className="eyebrow">La elección de la comunidad</span>
          <h2 id="top-products-heading">Los productos favoritos</h2>
          <p>
            Todos los productos publicados de esta categoría participan. Vota los que más te gustan.
          </p>
        </div>
      </div>
      {products.length ? (
        <>
          <div className="top-podium" aria-label="Podio de productos">
            {products.slice(0, 3).map((product) => (
              <TopProductCard key={product.id} product={product} podium />
            ))}
          </div>
          {products.length > 3 && (
            <div className="top-list" aria-label="Resto del ranking">
              {products.slice(3).map((product) => (
                <TopProductCard key={product.id} product={product} podium={false} />
              ))}
            </div>
          )}
        </>
      ) : (
        <p className="top-empty">
          Los productos de esta categoría aparecerán aquí en cuanto se publiquen.
        </p>
      )}
      {error && (
        <p role="alert" className="top-error">
          {error}
        </p>
      )}
    </section>
  );
}
