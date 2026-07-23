import { useState } from "react";
import type { Editor } from "@tiptap/react";
import {
  Bold,
  Italic,
  Underline,
  Strikethrough,
  Code,
  Eraser,
  Undo2,
  Redo2,
  List,
  ListOrdered,
  ListChecks,
  Quote,
  Code2,
  Minus,
  AlignLeft,
  AlignCenter,
  AlignRight,
  Highlighter,
  Link2,
  ImagePlus,
  Table as TableIcon,
  Maximize2,
  Minimize2,
  PackagePlus,
  Info,
  Rows3,
  Columns3,
  Trash2,
} from "lucide-react";
import { LinkDialog } from "./LinkDialog";
import { ImageDialog } from "./ImageDialog";
import { CALLOUT_VARIANTS } from "@/features/blog/utils/calloutVariants";
import { ALLOWED_TEXT_COLORS as TEXT_COLORS } from "@/features/blog/utils/textColors";

function ToolbarButton({
  active,
  disabled,
  onClick,
  label,
  children,
}: {
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
      className={`p-1.5 rounded shrink-0 disabled:opacity-30 ${active ? "bg-cyan-glow text-surface-900" : "hover:bg-surface-700"}`}
    >
      {children}
    </button>
  );
}

function Sep() {
  return <div className="w-px h-5 bg-surface-700 shrink-0 mx-0.5" aria-hidden="true" />;
}

export function EditorToolbar({
  editor,
  postId,
  fullscreen,
  onToggleFullscreen,
}: {
  editor: Editor;
  postId: string;
  fullscreen: boolean;
  onToggleFullscreen: () => void;
}) {
  const [linkOpen, setLinkOpen] = useState(false);
  const [imageOpen, setImageOpen] = useState(false);

  return (
    <div className="sticky top-0 z-10 bg-surface-900 border-b border-surface-700 px-2 py-1.5 flex items-center gap-0.5 overflow-x-auto min-w-0">
      <select
        aria-label="Estilo de párrafo"
        className="bg-surface-900 border border-surface-700 text-xs font-mono px-1.5 py-1 mr-1 shrink-0"
        value={
          editor.isActive("heading", { level: 2 })
            ? "h2"
            : editor.isActive("heading", { level: 3 })
              ? "h3"
              : editor.isActive("heading", { level: 4 })
                ? "h4"
                : "p"
        }
        onChange={(e) => {
          const v = e.target.value;
          if (v === "p") editor.chain().focus().setParagraph().run();
          else
            editor
              .chain()
              .focus()
              .toggleHeading({ level: Number(v[1]) as 2 | 3 | 4 })
              .run();
        }}
      >
        <option value="p">Párrafo</option>
        <option value="h2">Título H2</option>
        <option value="h3">Título H3</option>
        <option value="h4">Título H4</option>
      </select>

      <ToolbarButton
        label="Negrita"
        active={editor.isActive("bold")}
        onClick={() => editor.chain().focus().toggleBold().run()}
      >
        <Bold className="size-4" />
      </ToolbarButton>
      <ToolbarButton
        label="Cursiva"
        active={editor.isActive("italic")}
        onClick={() => editor.chain().focus().toggleItalic().run()}
      >
        <Italic className="size-4" />
      </ToolbarButton>
      <ToolbarButton
        label="Subrayado"
        active={editor.isActive("underline")}
        onClick={() => editor.chain().focus().toggleUnderline().run()}
      >
        <Underline className="size-4" />
      </ToolbarButton>
      <ToolbarButton
        label="Tachado"
        active={editor.isActive("strike")}
        onClick={() => editor.chain().focus().toggleStrike().run()}
      >
        <Strikethrough className="size-4" />
      </ToolbarButton>
      <ToolbarButton
        label="Código en línea"
        active={editor.isActive("code")}
        onClick={() => editor.chain().focus().toggleCode().run()}
      >
        <Code className="size-4" />
      </ToolbarButton>
      <ToolbarButton
        label="Limpiar formato"
        onClick={() => editor.chain().focus().clearNodes().unsetAllMarks().run()}
      >
        <Eraser className="size-4" />
      </ToolbarButton>

      <Sep />

      <ToolbarButton
        label="Lista con viñetas"
        active={editor.isActive("bulletList")}
        onClick={() => editor.chain().focus().toggleBulletList().run()}
      >
        <List className="size-4" />
      </ToolbarButton>
      <ToolbarButton
        label="Lista numerada"
        active={editor.isActive("orderedList")}
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
      >
        <ListOrdered className="size-4" />
      </ToolbarButton>
      <ToolbarButton
        label="Lista de tareas"
        active={editor.isActive("taskList")}
        onClick={() => editor.chain().focus().toggleTaskList().run()}
      >
        <ListChecks className="size-4" />
      </ToolbarButton>
      <ToolbarButton
        label="Cita"
        active={editor.isActive("blockquote")}
        onClick={() => editor.chain().focus().toggleBlockquote().run()}
      >
        <Quote className="size-4" />
      </ToolbarButton>
      <ToolbarButton
        label="Bloque de código"
        active={editor.isActive("codeBlock")}
        onClick={() => editor.chain().focus().toggleCodeBlock().run()}
      >
        <Code2 className="size-4" />
      </ToolbarButton>
      <ToolbarButton
        label="Separador"
        onClick={() => editor.chain().focus().setHorizontalRule().run()}
      >
        <Minus className="size-4" />
      </ToolbarButton>

      <Sep />

      <select
        aria-label="Insertar bloque informativo"
        className="bg-surface-900 border border-surface-700 text-xs font-mono px-1.5 py-1 shrink-0"
        value=""
        onChange={(e) => {
          const variant = e.target.value;
          if (!variant) return;
          editor
            .chain()
            .focus()
            .insertContent({
              type: "callout",
              attrs: { variant },
              content: [{ type: "paragraph" }],
            })
            .run();
          e.target.value = "";
        }}
      >
        <option value="">
          <Info className="size-4" /> Bloque...
        </option>
        {CALLOUT_VARIANTS.map((v) => (
          <option key={v.value} value={v.value}>
            {v.label}
          </option>
        ))}
      </select>

      <Sep />

      <ToolbarButton
        label="Alinear izquierda"
        active={editor.isActive({ textAlign: "left" })}
        onClick={() => editor.chain().focus().setTextAlign("left").run()}
      >
        <AlignLeft className="size-4" />
      </ToolbarButton>
      <ToolbarButton
        label="Centrar"
        active={editor.isActive({ textAlign: "center" })}
        onClick={() => editor.chain().focus().setTextAlign("center").run()}
      >
        <AlignCenter className="size-4" />
      </ToolbarButton>
      <ToolbarButton
        label="Alinear derecha"
        active={editor.isActive({ textAlign: "right" })}
        onClick={() => editor.chain().focus().setTextAlign("right").run()}
      >
        <AlignRight className="size-4" />
      </ToolbarButton>
      <ToolbarButton
        label="Resaltado"
        active={editor.isActive("highlight")}
        onClick={() => editor.chain().focus().toggleHighlight().run()}
      >
        <Highlighter className="size-4" />
      </ToolbarButton>

      <div
        className="flex items-center gap-1 shrink-0 px-1"
        role="group"
        aria-label="Color de texto"
      >
        {TEXT_COLORS.map((c) => (
          <button
            key={c.value}
            type="button"
            aria-label={`Color ${c.label}`}
            onClick={() => editor.chain().focus().setColor(c.value).run()}
            className="size-4 rounded-full border border-surface-600"
            style={{ backgroundColor: c.value }}
          />
        ))}
        <button
          type="button"
          aria-label="Quitar color"
          onClick={() => editor.chain().focus().unsetColor().run()}
          className="text-[10px] font-mono px-1 border border-surface-700"
        >
          X
        </button>
      </div>

      <Sep />

      <ToolbarButton
        label="Insertar o editar enlace"
        active={editor.isActive("link")}
        onClick={() => setLinkOpen(true)}
      >
        <Link2 className="size-4" />
      </ToolbarButton>
      <ToolbarButton label="Insertar imagen" onClick={() => setImageOpen(true)}>
        <ImagePlus className="size-4" />
      </ToolbarButton>
      <ToolbarButton
        label="Insertar producto recomendado"
        onClick={() =>
          editor
            .chain()
            .focus()
            .insertContent({ type: "productRecommendation", attrs: { mode: "manual" } })
            .run()
        }
      >
        <PackagePlus className="size-4" />
      </ToolbarButton>

      <Sep />

      <ToolbarButton
        label="Insertar tabla"
        onClick={() =>
          editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()
        }
      >
        <TableIcon className="size-4" />
      </ToolbarButton>
      <ToolbarButton
        label="Añadir fila"
        disabled={!editor.can().addRowAfter()}
        onClick={() => editor.chain().focus().addRowAfter().run()}
      >
        <Rows3 className="size-4" />
      </ToolbarButton>
      <ToolbarButton
        label="Añadir columna"
        disabled={!editor.can().addColumnAfter()}
        onClick={() => editor.chain().focus().addColumnAfter().run()}
      >
        <Columns3 className="size-4" />
      </ToolbarButton>
      <ToolbarButton
        label="Eliminar tabla"
        disabled={!editor.can().deleteTable()}
        onClick={() => editor.chain().focus().deleteTable().run()}
      >
        <Trash2 className="size-4" />
      </ToolbarButton>

      <Sep />

      <ToolbarButton
        label="Deshacer"
        disabled={!editor.can().undo()}
        onClick={() => editor.chain().focus().undo().run()}
      >
        <Undo2 className="size-4" />
      </ToolbarButton>
      <ToolbarButton
        label="Rehacer"
        disabled={!editor.can().redo()}
        onClick={() => editor.chain().focus().redo().run()}
      >
        <Redo2 className="size-4" />
      </ToolbarButton>

      <div className="flex-1" />

      <ToolbarButton
        label={fullscreen ? "Salir de pantalla completa" : "Pantalla completa"}
        onClick={onToggleFullscreen}
      >
        {fullscreen ? <Minimize2 className="size-4" /> : <Maximize2 className="size-4" />}
      </ToolbarButton>

      <LinkDialog editor={editor} open={linkOpen} onOpenChange={setLinkOpen} />
      <ImageDialog editor={editor} open={imageOpen} onOpenChange={setImageOpen} postId={postId} />
    </div>
  );
}
