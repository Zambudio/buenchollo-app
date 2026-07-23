import { useState } from "react";
import type { Editor } from "@tiptap/react";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

function isSafeHref(href: string): boolean {
  const trimmed = href.trim();
  if (!trimmed) return false;
  if (trimmed.startsWith("/")) return true;
  return /^https?:\/\//i.test(trimmed);
}

export function LinkDialog({
  editor,
  open,
  onOpenChange,
}: {
  editor: Editor;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [href, setHref] = useState(() => editor.getAttributes("link").href ?? "");
  const [newTab, setNewTab] = useState(() => editor.getAttributes("link").target === "_blank");
  const invalid = href.trim().length > 0 && !isSafeHref(href);

  const apply = () => {
    if (!isSafeHref(href)) return;
    const isExternal = !href.startsWith("/");
    editor
      .chain()
      .focus()
      .extendMarkRange("link")
      .setLink({
        href: href.trim(),
        target: newTab ? "_blank" : null,
        rel: isExternal && newTab ? "noopener noreferrer" : isExternal ? "noopener" : null,
      })
      .run();
    onOpenChange(false);
  };

  const remove = () => {
    editor.chain().focus().extendMarkRange("link").unsetLink().run();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Enlace</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <label
              className="text-xs font-mono uppercase text-muted-foreground"
              htmlFor="link-href"
            >
              URL
            </label>
            <input
              id="link-href"
              value={href}
              onChange={(e) => setHref(e.target.value)}
              placeholder="https://... o /ruta-interna"
              className={`mt-1 w-full bg-surface-900 border px-2 py-1.5 text-sm outline-none ${invalid ? "border-red-500" : "border-surface-700 focus:border-cyan-glow"}`}
            />
            {invalid && (
              <p className="text-xs text-red-400 mt-1">
                Protocolo no permitido. Usa http(s):// o una ruta interna que empiece por /.
              </p>
            )}
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={newTab} onChange={(e) => setNewTab(e.target.checked)} />
            Abrir en pestaña nueva
          </label>
        </div>
        <DialogFooter className="gap-2">
          <button
            type="button"
            onClick={remove}
            className="text-xs font-mono uppercase px-3 py-1.5 border border-surface-700"
          >
            Quitar enlace
          </button>
          <button
            type="button"
            onClick={apply}
            disabled={invalid || !href.trim()}
            className="text-xs font-mono uppercase px-3 py-1.5 bg-cyan-glow text-surface-900 disabled:opacity-50"
          >
            Aplicar
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
