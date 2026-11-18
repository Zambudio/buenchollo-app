import type { MouseEvent, ReactNode } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
} from "@/components/ui/pagination";

interface DealPaginationProps {
  currentPage: number;
  totalPages: number;
  loading?: boolean;
  onPageChange: (page: number) => void;
  /** URL de cada página. Si se indica, los controles son enlaces reales que los
   *  buscadores pueden seguir; el clic sigue navegando sin recargar. */
  hrefForPage?: (page: number) => string;
}

function visiblePages(current: number, total: number): Array<number | "ellipsis"> {
  if (total <= 7) return Array.from({ length: total }, (_, index) => index + 1);
  if (current <= 4) return [1, 2, 3, 4, 5, "ellipsis", total];
  if (current >= total - 3)
    return [1, "ellipsis", total - 4, total - 3, total - 2, total - 1, total];
  return [1, "ellipsis", current - 1, current, current + 1, "ellipsis", total];
}

interface PageControlProps {
  page: number;
  disabled: boolean;
  label: string;
  size: "default" | "icon";
  className?: string;
  current?: boolean;
  rel?: "prev" | "next";
  hrefForPage?: (page: number) => string;
  onPageChange: (page: number) => void;
  children: ReactNode;
}

function PageControl({
  page,
  disabled,
  label,
  size,
  className,
  current,
  rel,
  hrefForPage,
  onPageChange,
  children,
}: PageControlProps) {
  if (hrefForPage && !disabled) {
    const onClick = (event: MouseEvent<HTMLAnchorElement>) => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
      event.preventDefault();
      onPageChange(page);
    };
    return (
      <Button asChild variant="ghost" size={size} className={className}>
        <a
          href={hrefForPage(page)}
          rel={rel}
          onClick={onClick}
          aria-label={label}
          aria-current={current ? "page" : undefined}
        >
          {children}
        </a>
      </Button>
    );
  }
  return (
    <Button
      type="button"
      variant="ghost"
      size={size}
      onClick={() => onPageChange(page)}
      disabled={disabled}
      aria-label={label}
      aria-current={current ? "page" : undefined}
      className={className}
    >
      {children}
    </Button>
  );
}

export function DealPagination({
  currentPage,
  totalPages,
  loading = false,
  onPageChange,
  hrefForPage,
}: DealPaginationProps) {
  if (totalPages <= 1) return null;
  const shared = { hrefForPage, onPageChange };

  return (
    <Pagination aria-label="Páginas de chollos">
      <PaginationContent>
        <PaginationItem>
          <PageControl
            {...shared}
            page={currentPage - 1}
            disabled={loading || currentPage === 1}
            label="Ir a la página anterior"
            size="default"
            rel="prev"
            className="gap-1 px-2.5"
          >
            <ChevronLeft className="size-4" />
            <span className="hidden sm:inline">Anterior</span>
          </PageControl>
        </PaginationItem>

        {visiblePages(currentPage, totalPages).map((item, index) =>
          item === "ellipsis" ? (
            <PaginationItem key={`ellipsis-${index}`}>
              <PaginationEllipsis />
            </PaginationItem>
          ) : (
            <PaginationItem key={item}>
              <PageControl
                {...shared}
                page={item}
                disabled={loading}
                label={`Ir a la página ${item}`}
                size="icon"
                current={item === currentPage}
                className={item === currentPage ? "bg-accent text-accent-foreground" : undefined}
              >
                {item}
              </PageControl>
            </PaginationItem>
          ),
        )}

        <PaginationItem>
          <PageControl
            {...shared}
            page={currentPage + 1}
            disabled={loading || currentPage === totalPages}
            label="Ir a la página siguiente"
            size="default"
            rel="next"
            className="gap-1 px-2.5"
          >
            <span className="hidden sm:inline">Siguiente</span>
            <ChevronRight className="size-4" />
          </PageControl>
        </PaginationItem>
      </PaginationContent>
    </Pagination>
  );
}
