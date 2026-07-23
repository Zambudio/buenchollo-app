import { useState } from "react";
import type { Editor } from "@tiptap/react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAuth } from "@/hooks/useAuth";
import { useBlogImages } from "@/features/blog/hooks/useBlogImages";

export function ImageDialog({
  editor,
  open,
  onOpenChange,
  postId,
}: {
  editor: Editor;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  postId: string;
}) {
  const { user } = useAuth();
  const { uploadImage, uploading } = useBlogImages(user?.id, postId);
  const [src, setSrc] = useState("");
  const [alt, setAlt] = useState("");
  const [align, setAlign] = useState<"left" | "center" | "right">("left");
  const [width, setWidth] = useState<"normal" | "full">("normal");

  const reset = () => {
    setSrc("");
    setAlt("");
    setAlign("left");
    setWidth("normal");
  };

  const insert = () => {
    if (!src.trim()) return;
    if (!alt.trim()) {
      toast.error("El texto alternativo es obligatorio");
      return;
    }
    editor.chain().focus().setImage({ src: src.trim(), alt: alt.trim() }).run();
    // setImage no admite atributos extra directamente; los añadimos tras insertar.
    editor.chain().updateAttributes("image", { align, width }).run();
    reset();
    onOpenChange(false);
  };

  const handleFile = async (file: File) => {
    const url = await uploadImage(file);
    if (url) setSrc(url);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Insertar imagen</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <label className="text-xs font-mono uppercase border border-surface-700 px-3 py-2 block text-center cursor-pointer">
            {uploading ? "Subiendo..." : "Subir imagen"}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp,image/avif"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void handleFile(file);
              }}
            />
          </label>
          {src && <img src={src} alt="" className="max-h-32 rounded mx-auto" />}
          <div>
            <label className="text-xs font-mono uppercase text-muted-foreground" htmlFor="img-alt">
              Texto alternativo (obligatorio)
            </label>
            <input
              id="img-alt"
              value={alt}
              onChange={(e) => setAlt(e.target.value)}
              className="mt-1 w-full bg-surface-900 border border-surface-700 px-2 py-1.5 text-sm outline-none focus:border-cyan-glow"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <span className="text-xs font-mono uppercase text-muted-foreground">Alineación</span>
              <select
                value={align}
                onChange={(e) => setAlign(e.target.value as typeof align)}
                className="mt-1 w-full bg-surface-900 border border-surface-700 px-2 py-1.5 text-sm outline-none focus:border-cyan-glow"
              >
                <option value="left">Izquierda</option>
                <option value="center">Centro</option>
                <option value="right">Derecha</option>
              </select>
            </div>
            <div>
              <span className="text-xs font-mono uppercase text-muted-foreground">Ancho</span>
              <select
                value={width}
                onChange={(e) => setWidth(e.target.value as typeof width)}
                className="mt-1 w-full bg-surface-900 border border-surface-700 px-2 py-1.5 text-sm outline-none focus:border-cyan-glow"
              >
                <option value="normal">Normal</option>
                <option value="full">Ancho completo</option>
              </select>
            </div>
          </div>
        </div>
        <DialogFooter>
          <button
            type="button"
            onClick={insert}
            disabled={!src.trim() || !alt.trim()}
            className="text-xs font-mono uppercase px-3 py-1.5 bg-cyan-glow text-surface-900 disabled:opacity-50"
          >
            Insertar
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
