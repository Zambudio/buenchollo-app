import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Plus } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { DealPagination } from "@/features/deals/components/DealPagination";
import {
  useAdminPosts,
  useAdminCategories,
  usePublishPost,
  useArchivePost,
  useDeletePost,
} from "@/features/blog/hooks/useBlogAdmin";
import { AdminPostsTable } from "@/features/blog/components/admin/AdminPostsTable";

export const Route = createFileRoute("/admin/blog")({
  component: AdminBlog,
});

const PAGE_SIZE = 20;

function AdminBlog() {
  const [status, setStatus] = useState("all");
  const [categoryId, setCategoryId] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data: categories } = useAdminCategories();
  const { data, isLoading, isError } = useAdminPosts({
    status: status === "all" ? undefined : status,
    category_id: categoryId || undefined,
    search: search || undefined,
    page,
    page_size: PAGE_SIZE,
  });
  const publish = usePublishPost();
  const archive = useArchivePost();
  const del = useDeletePost();

  return (
    <div>
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <h2 className="font-mono text-sm uppercase text-cyan-glow">Gestión de blog</h2>
        <div className="flex items-center gap-2">
          <Link
            to="/admin/blog/categorias"
            className="border border-surface-700 text-xs font-mono uppercase px-3 py-2 hover:border-cyan-glow"
          >
            Categorías
          </Link>
          <Link
            to="/admin/blog/nuevo"
            className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2 flex items-center gap-2 hover:bg-foreground"
          >
            <Plus className="size-4" /> NUEVO ARTÍCULO
          </Link>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        <input
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          placeholder="Buscar por título..."
          aria-label="Buscar artículos"
          className="bg-surface-900 border border-surface-700 px-3 py-2 text-sm outline-none focus:border-cyan-glow flex-1 min-w-[200px]"
        />
        <select
          aria-label="Filtrar por estado"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
          className="bg-surface-900 border border-surface-700 px-3 py-2 text-xs font-mono uppercase outline-none focus:border-cyan-glow"
        >
          <option value="all">Todos los estados</option>
          <option value="draft">Borrador</option>
          <option value="scheduled">Programado</option>
          <option value="published">Publicado</option>
          <option value="archived">Archivado</option>
        </select>
        <select
          aria-label="Filtrar por categoría"
          value={categoryId}
          onChange={(e) => {
            setCategoryId(e.target.value);
            setPage(1);
          }}
          className="bg-surface-900 border border-surface-700 px-3 py-2 text-xs font-mono uppercase outline-none focus:border-cyan-glow"
        >
          <option value="">Todas las categorías</option>
          {categories?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      ) : isError ? (
        <div className="text-center py-12 border border-red-500/30 bg-red-500/5 text-red-400">
          Error al cargar los artículos.
        </div>
      ) : (
        <>
          <AdminPostsTable
            posts={data?.items ?? []}
            onPublish={(id) => publish.mutate(id)}
            onArchive={(id) => archive.mutate(id)}
            onDelete={(id) => del.mutate(id)}
          />
          {data && (
            <div className="mt-4">
              <DealPagination
                currentPage={data.page}
                totalPages={data.total_pages}
                onPageChange={setPage}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
