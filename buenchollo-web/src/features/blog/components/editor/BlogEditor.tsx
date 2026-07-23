import { useEditor, EditorContent } from "@tiptap/react";
import type { JSONContent } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import TextAlign from "@tiptap/extension-text-align";
import Highlight from "@tiptap/extension-highlight";
import { TextStyle } from "@tiptap/extension-text-style";
import Link from "@tiptap/extension-link";
import TaskList from "@tiptap/extension-task-list";
import TaskItem from "@tiptap/extension-task-item";
import { Table } from "@tiptap/extension-table";
import TableRow from "@tiptap/extension-table-row";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import Placeholder from "@tiptap/extension-placeholder";
import { useBlocker } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";

import { EditorToolbar } from "./EditorToolbar";
import { Callout } from "./extensions/callout";
import { ProductRecommendation } from "./extensions/productRecommendation";
import { BlogImage } from "./extensions/blogImage";
import { BlogColor } from "./extensions/blogColor";
import { countWords, extractPlainText, readingTimeMinutes } from "@/features/blog/utils/content";

export type SaveStatus = "idle" | "saving" | "saved" | "error";

const AUTOSAVE_DEBOUNCE_MS = 2000;

function buildExtensions() {
  return [
    StarterKit.configure({
      heading: { levels: [2, 3, 4] },
      link: false,
    }),
    Underline,
    TextAlign.configure({ types: ["heading", "paragraph"] }),
    Highlight,
    TextStyle,
    BlogColor,
    Link.configure({ openOnClick: false, autolink: false }),
    TaskList,
    TaskItem.configure({ nested: true }),
    Table.configure({ resizable: false }),
    TableRow,
    TableHeader,
    TableCell,
    BlogImage,
    Callout,
    ProductRecommendation,
    Placeholder.configure({ placeholder: "Escribe el contenido del artículo..." }),
  ];
}

export function BlogEditor({
  postId,
  initialContent,
  onChange,
  onAutosave,
  isPersisted,
}: {
  postId: string;
  initialContent: JSONContent;
  onChange?: (doc: JSONContent) => void;
  /** Solo se invoca si `isPersisted` es true (el artículo ya tiene id real);
   * nunca publica ni cambia el estado del artículo. */
  onAutosave?: (doc: JSONContent) => Promise<void>;
  isPersisted: boolean;
}) {
  const [fullscreen, setFullscreen] = useState(false);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [dirty, setDirty] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const editor = useEditor({
    immediatelyRender: false,
    extensions: buildExtensions(),
    content: initialContent,
    onUpdate: ({ editor }) => {
      const doc = editor.getJSON();
      setDirty(true);
      onChange?.(doc);
      if (isPersisted && onAutosave) {
        if (debounceRef.current) clearTimeout(debounceRef.current);
        setSaveStatus("saving");
        debounceRef.current = setTimeout(async () => {
          try {
            await onAutosave(doc);
            setSaveStatus("saved");
            setDirty(false);
          } catch {
            setSaveStatus("error");
          }
        }, AUTOSAVE_DEBOUNCE_MS);
      }
    },
  });

  // Ctrl+S guarda borrador (autoguardado inmediato), nunca publica.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        if (editor && onAutosave) {
          if (debounceRef.current) clearTimeout(debounceRef.current);
          setSaveStatus("saving");
          onAutosave(editor.getJSON())
            .then(() => {
              setSaveStatus("saved");
              setDirty(false);
            })
            .catch(() => setSaveStatus("error"));
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [editor, onAutosave]);

  // Avisa antes de cerrar/recargar la pestaña con cambios sin guardar.
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (!dirty) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  // Bloquea la navegación interna (TanStack Router) si hay cambios sin guardar.
  useBlocker({
    shouldBlockFn: () => {
      if (!dirty) return false;
      return !window.confirm("Hay cambios sin guardar. ¿Salir de todos modos?");
    },
  });

  if (!editor) return null;

  const text = extractPlainText(editor.getJSON());
  const words = countWords(text);
  const minutes = readingTimeMinutes(words);

  return (
    <div
      className={
        fullscreen
          ? "fixed inset-0 z-50 bg-background flex flex-col"
          : "flex flex-col w-full min-w-0"
      }
    >
      <EditorToolbar
        editor={editor}
        postId={postId}
        fullscreen={fullscreen}
        onToggleFullscreen={() => setFullscreen((v) => !v)}
      />
      <div
        className={`flex-1 overflow-y-auto border border-t-0 border-surface-700 bg-surface-900 ${fullscreen ? "" : "min-h-[400px]"}`}
      >
        <EditorContent
          editor={editor}
          className="prose prose-invert max-w-none p-4 focus:outline-none blog-editor-content"
        />
      </div>
      <div className="flex items-center justify-between text-xs font-mono text-muted-foreground px-2 py-1.5 border border-t-0 border-surface-700">
        <span>
          {words} palabras · {minutes} min de lectura
        </span>
        <span aria-live="polite">
          {saveStatus === "saving" && "Guardando..."}
          {saveStatus === "saved" && "Guardado"}
          {saveStatus === "error" && <span className="text-red-400">Error al guardar</span>}
          {saveStatus === "idle" && dirty && "Cambios sin guardar"}
        </span>
      </div>
    </div>
  );
}
