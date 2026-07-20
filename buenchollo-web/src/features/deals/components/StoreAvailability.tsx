import { Link } from "@tanstack/react-router";

export function StoreAvailability({
  store,
}: {
  store: { id: string; name: string; slug: string };
}) {
  return (
    <span className="store availability meta">
      <span>Disponible en</span>
      <Link to="/explorar" search={{ store: store.id }} aria-label={`Ver chollos de ${store.name}`}>
        {store.name}
      </Link>
    </span>
  );
}
