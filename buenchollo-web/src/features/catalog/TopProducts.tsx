import { Link } from "@tanstack/react-router";
import { ArrowUpRight, Crown, ThumbsUp } from "lucide-react";
import { useEffect, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { formatPrice } from "@/lib/format";
import { catalogService, type TopProduct } from "@/services/api/catalog";

export function TopProducts({
  slug,
  initialProducts,
}: {
  slug: string;
  initialProducts: TopProduct[];
}) {
  const { user } = useAuth();
  const [products, setProducts] = useState(initialProducts);
  const [myVotes, setMyVotes] = useState<Set<string>>(new Set());
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setProducts(initialProducts);
  }, [initialProducts]);

  useEffect(() => {
    if (!user || !products.length) {
      setMyVotes(new Set());
      return;
    }
    let cancelled = false;
    catalogService
      .myVotes(products.map((product) => product.id))
      .then((ids) => {
        if (!cancelled) setMyVotes(new Set(ids));
      })
      .catch(() => {
        if (!cancelled) setMyVotes(new Set());
      });
    return () => {
      cancelled = true;
    };
  }, [user, products, slug]);

  const vote = async (id: string) => {
    setPending(id);
    setError("");
    try {
      const result = await catalogService.vote(id);
      setMyVotes((previous) => {
        const next = new Set(previous);
        if (result.voted) next.add(id);
        else next.delete(id);
        return next;
      });
      setProducts((previous) =>
        previous.map((product) =>
          product.id === id
            ? { ...product, vote_count: product.vote_count + (result.voted ? 1 : -1) }
            : product,
        ),
      );
      try {
        setProducts(await catalogService.top(slug));
      } catch {
        setError("Voto guardado. No hemos podido actualizar las posiciones; recarga la página.");
      }
    } catch {
      setError("No hemos podido registrar tu voto. Inténtalo de nuevo.");
    } finally {
      setPending(null);
    }
  };

  const card = (product: TopProduct, podium: boolean) => (
    <article
      key={product.id}
      className={podium ? `top-podium-card top-place-${product.position}` : "top-list-card"}
    >
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
      {user ? (
        <button
          className={`top-vote ${myVotes.has(product.id) ? "is-voted" : ""}`}
          type="button"
          aria-label={`${myVotes.has(product.id) ? "Retirar voto a" : "Votar por"} ${product.title}`}
          aria-pressed={myVotes.has(product.id)}
          disabled={pending !== null}
          onClick={() => void vote(product.id)}
        >
          <ThumbsUp size={15} aria-hidden="true" /> <span>{product.vote_count}</span>
        </button>
      ) : (
        <Link
          className="top-vote"
          to="/login"
          aria-label={`Accede para votar por ${product.title}`}
        >
          <ThumbsUp size={15} aria-hidden="true" /> <span>{product.vote_count}</span>
        </Link>
      )}
    </article>
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
            {products.slice(0, 3).map((product) => card(product, true))}
          </div>
          {products.length > 3 && (
            <div className="top-list" aria-label="Puestos del 4 al 10">
              {products.slice(3, 10).map((product) => card(product, false))}
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
