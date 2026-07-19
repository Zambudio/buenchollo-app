/**
 * Panel lateral de publicación en Telegram.
 * Se abre desde el formulario de admin cuando el usuario quiere previsualizar
 * y editar el post antes de publicar.
 */

import { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Loader2, Plus, Send, X } from "lucide-react";
import { toast } from "sonner";
import {
  telegramApi,
  type TelegramChannel,
  type TelegramGenerateRequest,
} from "@/services/api/telegram";

interface TelegramPanelProps {
  /** Datos del deal con los que generar el post */
  dealData: TelegramGenerateRequest & {
    images?: string[];
    image_url?: string | null;
  };
  onClose: () => void;
}

export function TelegramPanel({ dealData, onClose }: TelegramPanelProps) {
  const [text, setText] = useState("");
  const [generating, setGenerating] = useState(false);
  const [publishing, setPublishing] = useState(false);

  // Imágenes
  const images: string[] = dealData.images?.length
    ? dealData.images
    : dealData.image_url
      ? [dealData.image_url]
      : [];
  const [imageIdx, setImageIdx] = useState(0);

  // Canales
  const [channels, setChannels] = useState<TelegramChannel[]>([]);
  const [channelId, setChannelId] = useState("");

  // Categorías
  const [categories, setCategories] = useState<string[]>([]);
  const [suggested, setSuggested] = useState<string[]>([]);
  const [selectedCat, setSelectedCat] = useState("");
  const [newCat, setNewCat] = useState("");
  const [addingCat, setAddingCat] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // ── Al montar: cargar canales + categorías + generar texto ─────────────────
  useEffect(() => {
    Promise.all([telegramApi.getChannels(), telegramApi.getCategories()])
      .then(([chs, cats]) => {
        setChannels(chs);
        // Por defecto: primer canal (Admin si existe)
        const firstCh = chs[0];
        if (firstCh) setChannelId(firstCh.id);
        setCategories(cats);
        const firstCat = cats[0];
        if (firstCat) setSelectedCat(firstCat);
      })
      .catch(() => toast.error("No se pudieron cargar canales/categorías"));

    handleGenerate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Generar / regenerar texto ──────────────────────────────────────────────
  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const result = await telegramApi.generate({
        title: dealData.title,
        current_price: dealData.current_price,
        previous_price: dealData.previous_price,
        discount_percentage: dealData.discount_percentage,
        description: dealData.description,
        affiliate_url: dealData.affiliate_url,
        expires_at: dealData.expires_at,
      });
      setText(result.text);
      setSuggested(result.suggested_categories);
    } catch {
      toast.error("Error generando el post. Puedes escribirlo manualmente.");
    } finally {
      setGenerating(false);
    }
  };

  // ── Insertar categoría al final del texto ──────────────────────────────────
  const appendCategory = (cat: string) => {
    if (!cat) return;
    setText((prev) => {
      const base = prev.trimEnd();
      // No duplicar si ya está
      if (base.includes(cat)) return prev;
      // Si la última línea ya es un hashtag → nueva línea sin línea en blanco
      const lastLine = base.split("\n").at(-1)?.trim() ?? "";
      const separator = lastLine.startsWith("#") ? "\n" : "\n\n";
      return base + separator + cat;
    });
    textareaRef.current?.focus();
  };

  // ── Añadir categoría nueva al catálogo ────────────────────────────────────
  const handleAddCategory = async () => {
    const cat = newCat.trim();
    if (!cat) return;
    setAddingCat(true);
    try {
      const updated = await telegramApi.addCategory(cat);
      setCategories(updated);
      setNewCat("");
      toast.success(`Categoría "${cat}" añadida al catálogo`);
    } catch {
      toast.error("Error añadiendo categoría");
    } finally {
      setAddingCat(false);
    }
  };

  // ── Publicar ───────────────────────────────────────────────────────────────
  const handlePublish = async () => {
    if (!text.trim()) {
      toast.error("El mensaje está vacío");
      return;
    }
    if (!channelId) {
      toast.error("Selecciona un canal");
      return;
    }

    setPublishing(true);
    try {
      const selectedImage = images[imageIdx] ?? null;
      await telegramApi.notify({
        text,
        image_url: selectedImage,
        channel_id: channelId,
      });
      toast.success("✅ Publicado en Telegram");
      onClose();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Error desconocido";
      toast.error("Telegram: " + msg);
    } finally {
      setPublishing(false);
    }
  };

  const inputCls =
    "w-full bg-surface-900 border border-surface-700 px-3 py-2 font-mono text-sm outline-none focus:border-cyan-glow";

  return (
    // Overlay
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Fondo semitransparente clickeable para cerrar */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Panel lateral */}
      <div className="relative z-10 w-full max-w-lg bg-surface-800 border-l border-surface-700 flex flex-col h-full overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-surface-700 shrink-0">
          <div className="flex items-center gap-2">
            <Send className="size-4 text-cyan-glow" />
            <span className="font-mono text-sm uppercase text-cyan-glow font-bold">
              Publicar en Telegram
            </span>
          </div>
          <button onClick={onClose} className="p-1 hover:text-alert-red">
            <X className="size-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* ── Mensaje ─────────────────────────────────────────────────── */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="font-mono text-[10px] uppercase text-muted-foreground">Mensaje</span>
              <button
                type="button"
                onClick={handleGenerate}
                disabled={generating}
                className="font-mono text-[10px] text-cyan-glow hover:underline flex items-center gap-1 disabled:opacity-50"
              >
                {generating && <Loader2 className="size-3 animate-spin" />}
                {generating ? "Generando..." : "↺ Regenerar"}
              </button>
            </div>
            {generating ? (
              <div className="flex items-center justify-center h-40 border border-surface-700 bg-surface-900">
                <Loader2 className="size-5 animate-spin text-cyan-glow" />
              </div>
            ) : (
              <textarea
                ref={textareaRef}
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={12}
                className={inputCls + " resize-y text-xs leading-relaxed"}
                placeholder="El texto del post aparecerá aquí..."
              />
            )}
          </div>

          {/* ── Selector de imagen ──────────────────────────────────────── */}
          {images.length > 0 && (
            <div>
              <span className="font-mono text-[10px] uppercase text-muted-foreground block mb-2">
                Imagen ({imageIdx + 1} / {images.length})
              </span>
              <div className="relative border border-surface-700 bg-surface-900 aspect-video overflow-hidden">
                <img src={images[imageIdx]} alt="" className="w-full h-full object-contain" />
                {images.length > 1 && (
                  <>
                    <button
                      type="button"
                      onClick={() => setImageIdx((i) => Math.max(0, i - 1))}
                      disabled={imageIdx === 0}
                      className="absolute left-1 top-1/2 -translate-y-1/2 bg-surface-900/80 p-1 hover:text-cyan-glow disabled:opacity-30"
                    >
                      <ChevronLeft className="size-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => setImageIdx((i) => Math.min(images.length - 1, i + 1))}
                      disabled={imageIdx === images.length - 1}
                      className="absolute right-1 top-1/2 -translate-y-1/2 bg-surface-900/80 p-1 hover:text-cyan-glow disabled:opacity-30"
                    >
                      <ChevronRight className="size-4" />
                    </button>
                  </>
                )}
              </div>
              {/* Miniaturas */}
              {images.length > 1 && (
                <div className="flex gap-1 mt-2 overflow-x-auto">
                  {images.map((url, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setImageIdx(i)}
                      className={`shrink-0 w-12 h-12 border-2 overflow-hidden ${
                        i === imageIdx ? "border-cyan-glow" : "border-surface-700"
                      }`}
                    >
                      <img src={url} alt="" className="w-full h-full object-cover" />
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── Canal destino ────────────────────────────────────────────── */}
          <div>
            <label className="font-mono text-[10px] uppercase text-muted-foreground block mb-1">
              Canal destino
            </label>
            <select
              value={channelId}
              onChange={(e) => setChannelId(e.target.value)}
              className={inputCls}
            >
              {channels.length === 0 && <option value="">Sin canales configurados</option>}
              {channels.map((ch) => (
                <option key={ch.id} value={ch.id}>
                  {ch.name}
                </option>
              ))}
            </select>
          </div>

          {/* ── Categorías ───────────────────────────────────────────────── */}
          <div className="border border-surface-700 p-3 space-y-3">
            <span className="font-mono text-[10px] uppercase text-cyan-glow block">
              Categorías del canal
            </span>

            {/* Sugeridas por IA */}
            {suggested.length > 0 && (
              <div>
                <span className="font-mono text-[10px] text-muted-foreground block mb-1">
                  Sugeridas por IA:
                </span>
                <div className="flex flex-wrap gap-1">
                  {suggested.map((cat) => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => appendCategory(cat)}
                      className="font-mono text-[10px] px-2 py-1 bg-cyan-glow/10 text-cyan-glow border border-cyan-glow/30 hover:bg-cyan-glow/20"
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Catálogo completo */}
            <div className="flex gap-2">
              <select
                value={selectedCat}
                onChange={(e) => setSelectedCat(e.target.value)}
                className={inputCls + " flex-1"}
              >
                {categories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => appendCategory(selectedCat)}
                className="border border-surface-700 px-3 font-mono text-xs hover:border-cyan-glow whitespace-nowrap"
              >
                Añadir
              </button>
            </div>

            {/* Nueva categoría */}
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="#NuevaCategoria"
                value={newCat}
                onChange={(e) => setNewCat(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleAddCategory();
                  }
                }}
                className={inputCls + " flex-1"}
              />
              <button
                type="button"
                onClick={handleAddCategory}
                disabled={addingCat || !newCat.trim()}
                className="border border-surface-700 px-3 font-mono text-xs hover:border-cyan-glow disabled:opacity-50 flex items-center gap-1"
              >
                {addingCat ? (
                  <Loader2 className="size-3 animate-spin" />
                ) : (
                  <Plus className="size-3" />
                )}
                Nueva
              </button>
            </div>
          </div>
        </div>

        {/* Footer fijo */}
        <div className="shrink-0 px-5 py-4 border-t border-surface-700">
          <button
            type="button"
            onClick={handlePublish}
            disabled={publishing || !text.trim() || !channelId}
            className="w-full bg-cyan-glow text-surface-900 font-mono text-sm font-bold py-3 flex items-center justify-center gap-2 hover:bg-foreground disabled:opacity-50"
          >
            {publishing ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
            {publishing ? "PUBLICANDO..." : "🚀 PUBLICAR AHORA"}
          </button>
        </div>
      </div>
    </div>
  );
}
