import { mergeAttributes, Node } from "@tiptap/core";
import { NodeViewContent, NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";
import type { NodeViewProps } from "@tiptap/react";
import { CALLOUT_VARIANTS } from "@/features/blog/utils/calloutVariants";

export { CALLOUT_VARIANTS };

function CalloutView({ node, updateAttributes }: NodeViewProps) {
  const variant = (node.attrs.variant as string) ?? "info";
  return (
    <NodeViewWrapper
      data-variant={variant}
      className="my-3 border-l-4 rounded-r px-4 py-3 bg-surface-800/60 blog-callout"
      style={{
        borderColor:
          variant === "warning"
            ? "#f87171"
            : variant === "tip"
              ? "#4ade80"
              : variant === "verdict"
                ? "#a78bfa"
                : "#22d3ee",
      }}
    >
      <select
        contentEditable={false}
        value={variant}
        onChange={(e) => updateAttributes({ variant: e.target.value })}
        className="mb-2 bg-surface-900 border border-surface-700 text-xs font-mono uppercase px-2 py-1 outline-none focus:border-cyan-glow"
        aria-label="Tipo de bloque informativo"
      >
        {CALLOUT_VARIANTS.map((v) => (
          <option key={v.value} value={v.value}>
            {v.label}
          </option>
        ))}
      </select>
      <NodeViewContent className="prose-sm" />
    </NodeViewWrapper>
  );
}

export const Callout = Node.create({
  name: "callout",
  group: "block",
  content: "paragraph+",
  defining: true,

  addAttributes() {
    return {
      variant: { default: "info" },
    };
  },

  parseHTML() {
    return [{ tag: "div[data-callout]" }];
  },

  renderHTML({ HTMLAttributes, node }) {
    return [
      "div",
      mergeAttributes(HTMLAttributes, {
        "data-callout": "",
        "data-variant": node.attrs.variant,
      }),
      0,
    ];
  },

  addNodeView() {
    return ReactNodeViewRenderer(CalloutView);
  },
});
