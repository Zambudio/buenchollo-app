import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { Star, Eye, Pencil, Send, Archive, Trash2 } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import type { BlogPostAdminListItem, BlogPostStatus } from "@/services/api/blog";

const STATUS_LABEL: Record<BlogPostStatus, string> = {
  draft: "Borrador",
  scheduled: "Programado",
  published: "Publicado",
  archived: "Archivado",
};

const STATUS_CLASS: Record<BlogPostStatus, string> = {
  draft: "text-muted-foreground border-surface-600",
  scheduled: "text-amber-400 border-amber-500/50",
  published: "text-cyan-glow border-cyan-glow/50",
  archived: "text-red-400 border-red-500/40",
};

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function AdminPostsTable({
  posts,
  onPublish,
  onArchive,
  onDelete,
}: {
  posts: BlogPostAdminListItem[];
  onPublish: (id: string) => void;
  onArchive: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const [pendingDelete, setPendingDelete] = useState<BlogPostAdminListItem | null>(null);

  if (posts.length === 0) {
    return (
      <div className="text-center py-12 border border-surface-700 bg-surface-800/30 text-muted-foreground">
        No hay artículos con estos filtros.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto border border-surface-700">
      <table className="w-full text-sm">
        <thead className="bg-surface-800 font-mono text-[10px] uppercase text-muted-foreground">
          <tr>
            <th className="p-2 text-left">Artículo</th>
            <th className="p-2 text-left">Categoría</th>
            <th className="p-2 text-left">Estado</th>
            <th className="p-2 text-left">Autor</th>
            <th className="p-2 text-left">Actualizado</th>
            <th className="p-2 text-left">Publicación</th>
            <th className="p-2 text-center">★</th>
            <th className="p-2 text-right">Acciones</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-surface-700">
          {posts.map((post) => (
            <tr key={post.id} className="hover:bg-surface-800/50">
              <td className="p-2">
                <div className="flex items-center gap-2">
                  {post.cover_image_url ? (
                    <img
                      src={post.cover_image_url}
                      alt=""
                      className="size-10 object-cover rounded shrink-0"
                    />
                  ) : (
                    <div className="size-10 bg-surface-800 rounded shrink-0" />
                  )}
                  <span className="font-medium line-clamp-2">{post.title}</span>
                </div>
              </td>
              <td className="p-2 text-muted-foreground">{post.category?.name ?? "—"}</td>
              <td className="p-2">
                <span
                  className={`border px-2 py-0.5 rounded font-mono text-[10px] uppercase ${STATUS_CLASS[post.status]}`}
                >
                  {STATUS_LABEL[post.status]}
                </span>
              </td>
              <td className="p-2 text-muted-foreground">{post.author?.display_name ?? "—"}</td>
              <td className="p-2 text-muted-foreground">{formatDate(post.updated_at)}</td>
              <td className="p-2 text-muted-foreground">
                {post.status === "scheduled"
                  ? formatDate(post.scheduled_for)
                  : formatDate(post.published_at)}
              </td>
              <td className="p-2 text-center">
                {post.is_featured && <Star className="size-4 text-cyan-glow inline fill-current" />}
              </td>
              <td className="p-2">
                <div className="flex items-center justify-end gap-1">
                  <Link
                    to="/admin/blog/$postId"
                    params={{ postId: post.id }}
                    aria-label="Editar artículo"
                    className="p-1.5 hover:text-cyan-glow"
                  >
                    <Pencil className="size-4" />
                  </Link>
                  <Link
                    to="/admin/blog/$postId/preview"
                    params={{ postId: post.id }}
                    aria-label="Previsualizar artículo"
                    className="p-1.5 hover:text-cyan-glow"
                  >
                    <Eye className="size-4" />
                  </Link>
                  {post.status !== "published" && (
                    <button
                      type="button"
                      aria-label="Publicar artículo"
                      onClick={() => onPublish(post.id)}
                      className="p-1.5 hover:text-cyan-glow"
                    >
                      <Send className="size-4" />
                    </button>
                  )}
                  {post.status !== "archived" && (
                    <button
                      type="button"
                      aria-label="Archivar artículo"
                      onClick={() => onArchive(post.id)}
                      className="p-1.5 hover:text-amber-400"
                    >
                      <Archive className="size-4" />
                    </button>
                  )}
                  <button
                    type="button"
                    aria-label="Eliminar artículo"
                    onClick={() => setPendingDelete(post)}
                    className="p-1.5 hover:text-red-400"
                  >
                    <Trash2 className="size-4" />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <AlertDialog open={!!pendingDelete} onOpenChange={(open) => !open && setPendingDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Eliminar artículo</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción eliminará permanentemente «{pendingDelete?.title}». No se puede deshacer.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (pendingDelete) onDelete(pendingDelete.id);
                setPendingDelete(null);
              }}
            >
              Eliminar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
