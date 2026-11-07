import { Link } from "@tanstack/react-router";
import { ArrowRight, ChevronLeft, ChevronRight, Crown, Package, Pause, Play } from "lucide-react";
import { useEffect, useState } from "react";
import type { BannerTop } from "./bannerTops";

export function TopBanner({ tops }: { tops: BannerTop[] }) {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(true);
  const activeIndex = tops.length ? index % tops.length : 0;
  const top = tops[activeIndex];
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    if (tops.length < 2 || paused || hovered || focused || reducedMotion) return;
    const timer = window.setInterval(() => {
      if (!document.hidden) setIndex((value) => (value + 1) % tops.length);
    }, 8000);
    return () => window.clearInterval(timer);
  }, [tops.length, paused, hovered, focused, reducedMotion]);
  const change = (direction: number) => {
    setPaused(true);
    setIndex((value) => (value + direction + tops.length) % tops.length);
  };
  return (
    <section
      className="top-banner"
      aria-labelledby="top-banner-heading"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocusCapture={() => setFocused(true)}
      onBlurCapture={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setFocused(false);
      }}
    >
      <div className="top-banner-copy">
        <span className="eyebrow">Tops de la comunidad</span>
        <h2 id="top-banner-heading">
          El próximo nº 1<br />
          <span>lo eliges tú.</span>
        </h2>
        <p>Descubre los tops por categoría y vota tus productos favoritos.</p>
        <Link to="/categorias" className="top-banner-cta">
          Ver tops y votar <ArrowRight size={17} aria-hidden="true" />
        </Link>
      </div>
      {top ? (
        <div className="top-banner-showcase">
          <Link className="top-banner-category" to="/categoria/$slug" params={{ slug: top.slug }}>
            Top {top.name} <ArrowRight size={14} aria-hidden="true" />
          </Link>
          <div className="top-banner-podium" aria-label={`Primeros puestos de ${top.name}`}>
            {[2, 1, 3].map((position) => {
              const product = top.products.find((p) => p.position === position);
              return (
                <div key={position} className={`top-banner-place top-banner-place-${position}`}>
                  {product ? (
                    <Link
                      to="/categoria/$slug"
                      params={{ slug: top.slug }}
                      className="top-banner-product"
                      aria-label={`Puesto ${position}: ${product.title}. Ver top ${top.name}`}
                      title={product.title}
                    >
                      <Package className="top-banner-image-fallback" aria-hidden="true" />
                      {product.image_url && (
                        <img
                          key={product.image_url}
                          src={product.image_url}
                          alt=""
                          width="112"
                          height="112"
                          decoding="async"
                          onError={(event) => {
                            event.currentTarget.style.visibility = "hidden";
                          }}
                        />
                      )}
                      {position === 1 && (
                        <span className="top-banner-crown">
                          <Crown size={16} aria-hidden="true" />
                        </span>
                      )}
                    </Link>
                  ) : (
                    <span className="top-banner-vacant" aria-hidden="true">
                      —
                    </span>
                  )}
                  <span className="top-banner-step" aria-hidden="true">
                    {product ? position : "—"}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="top-banner-controls">
            {tops.length > 1 && (
              <button type="button" onClick={() => change(-1)} aria-label="Top anterior">
                <ChevronLeft size={16} />
              </button>
            )}
            <span>
              {top.products.every((p) => p.vote_count === 0)
                ? "Estrena los votos de este top"
                : "Elegidos por la comunidad"}
            </span>
            {tops.length > 1 && (
              <>
                <button type="button" onClick={() => change(1)} aria-label="Siguiente top">
                  <ChevronRight size={16} />
                </button>
                {!reducedMotion && (
                  <button
                    type="button"
                    onClick={() => setPaused((value) => !value)}
                    aria-label={paused ? "Activar rotación de tops" : "Pausar rotación de tops"}
                  >
                    {paused ? <Play size={14} /> : <Pause size={14} />}
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      ) : (
        <div className="top-banner-empty" aria-hidden="true">
          <Crown size={86} strokeWidth={1.2} />
        </div>
      )}
    </section>
  );
}
