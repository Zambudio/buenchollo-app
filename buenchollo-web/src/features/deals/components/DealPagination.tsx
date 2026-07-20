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
}

function visiblePages(current: number, total: number): Array<number | "ellipsis"> {
  if (total <= 7) return Array.from({ length: total }, (_, index) => index + 1);
  if (current <= 4) return [1, 2, 3, 4, 5, "ellipsis", total];
  if (current >= total - 3)
    return [1, "ellipsis", total - 4, total - 3, total - 2, total - 1, total];
  return [1, "ellipsis", current - 1, current, current + 1, "ellipsis", total];
}

export function DealPagination({
  currentPage,
  totalPages,
  loading = false,
  onPageChange,
}: DealPaginationProps) {
  if (totalPages <= 1) return null;

  return (
    <Pagination aria-label="Páginas de chollos">
      <PaginationContent>
        <PaginationItem>
          <Button
            type="button"
            variant="ghost"
            size="default"
            onClick={() => onPageChange(currentPage - 1)}
            disabled={loading || currentPage === 1}
            aria-label="Ir a la página anterior"
            className="gap-1 px-2.5"
          >
            <ChevronLeft className="size-4" />
            <span className="hidden sm:inline">Anterior</span>
          </Button>
        </PaginationItem>

        {visiblePages(currentPage, totalPages).map((item, index) =>
          item === "ellipsis" ? (
            <PaginationItem key={`ellipsis-${index}`}>
              <PaginationEllipsis />
            </PaginationItem>
          ) : (
            <PaginationItem key={item}>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => onPageChange(item)}
                disabled={loading}
                aria-label={`Ir a la página ${item}`}
                aria-current={item === currentPage ? "page" : undefined}
                className={item === currentPage ? "bg-accent text-accent-foreground" : undefined}
              >
                {item}
              </Button>
            </PaginationItem>
          ),
        )}

        <PaginationItem>
          <Button
            type="button"
            variant="ghost"
            size="default"
            onClick={() => onPageChange(currentPage + 1)}
            disabled={loading || currentPage === totalPages}
            aria-label="Ir a la página siguiente"
            className="gap-1 px-2.5"
          >
            <span className="hidden sm:inline">Siguiente</span>
            <ChevronRight className="size-4" />
          </Button>
        </PaginationItem>
      </PaginationContent>
    </Pagination>
  );
}
