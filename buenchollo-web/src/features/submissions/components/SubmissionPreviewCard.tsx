/** Vista previa de la tarjeta tal como se verá en el listado: es la misma
 *  `DealCardView` que usa `DealCard`, en modo `preview` (sin enlaces ni acciones). */
import { useState } from "react";
import { DealCardView } from "@/features/deals/components/DealCardView";
import { calculateDiscount, formatPrice } from "@/lib/format";

interface SubmissionPreviewCardProps {
  title: string;
  currentPrice: number | null;
  previousPrice: number | null;
  images: string[];
  storeName: string | null;
}

export function SubmissionPreviewCard({
  title,
  currentPrice,
  previousPrice,
  images,
  storeName,
}: SubmissionPreviewCardProps) {
  const [now] = useState(() => new Date().toISOString());
  const shownTitle = title.trim() || "Título del chollo";
  const discount = calculateDiscount(currentPrice, previousPrice);
  const store = storeName?.trim();

  return (
    <figure aria-label="Vista previa de la tarjeta" className="m-0">
      <DealCardView
        preview
        deal={{
          id: "preview",
          slug: "preview",
          title: shownTitle,
          image_url: images[0] ?? null,
          images,
          current_price: currentPrice ?? 0,
          previous_price: previousPrice,
          discount_percentage: null,
          temperature: 0,
          published_at: now,
          store: store ? { id: "preview", name: store, slug: "" } : null,
        }}
        temperature={0}
      />
      <figcaption className="sr-only">
        {shownTitle}
        {currentPrice != null ? `, ${formatPrice(currentPrice)}` : ""}
        {discount ? `, ${discount}% de descuento` : ""}
        {store ? `, en ${store}` : ""}
      </figcaption>
    </figure>
  );
}
