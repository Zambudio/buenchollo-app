import { Link } from "@tanstack/react-router";

export function StoreAvailability({
  store,
  linked = true,
}: {
  store: { id: string; name: string; slug: string };
  linked?: boolean;
}) {
  return (
    <span className="store availability meta">
      <span>Disponible en</span>
      {linked ? (
        <Link
          to="/explorar"
          search={{ store: store.id }}
          aria-label={`Ver chollos de ${store.name}`}
        >
          {store.name}
        </Link>
      ) : (
        <span className="text-cyan-glow">{store.name}</span>
      )}
    </span>
  );
}
