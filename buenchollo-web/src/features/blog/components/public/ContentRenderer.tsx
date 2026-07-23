import { Fragment, type ReactNode } from "react";
import type { JSONContent } from "@tiptap/core";
import type { BlogDealSummary } from "@/services/api/blog";
import { ProductRecommendationCard } from "./ProductRecommendationCard";
import { slugify } from "@/features/blog/utils/slugify";

/** Renderer público controlado del documento Tiptap: solo contempla los
 * nodos y marcas que el backend valida (`domain/content.py`). Nunca usa
 * `dangerouslySetInnerHTML` — todo pasa por elementos React tipados. */

const CALLOUT_STYLES: Record<string, { border: string; label: string }> = {
  info: { border: "#22d3ee", label: "Información" },
  tip: { border: "#4ade80", label: "Consejo" },
  warning: { border: "#f87171", label: "Advertencia" },
  verdict: { border: "#a78bfa", label: "Veredicto" },
};

function renderMarks(text: string, marks: JSONContent["marks"], key: string): ReactNode {
  let node: ReactNode = text;
  for (const mark of marks ?? []) {
    switch (mark.type) {
      case "bold":
        node = <strong key={key}>{node}</strong>;
        break;
      case "italic":
        node = <em key={key}>{node}</em>;
        break;
      case "underline":
        node = <u key={key}>{node}</u>;
        break;
      case "strike":
        node = <s key={key}>{node}</s>;
        break;
      case "code":
        node = <code key={key}>{node}</code>;
        break;
      case "highlight":
        node = <mark key={key}>{node}</mark>;
        break;
      case "textStyle": {
        const color = mark.attrs?.color as string | undefined;
        node = color ? (
          <span key={key} style={{ color }}>
            {node}
          </span>
        ) : (
          node
        );
        break;
      }
      case "link": {
        const href = (mark.attrs?.href as string) ?? "#";
        const isInternal = href.startsWith("/");
        const target = mark.attrs?.target as string | undefined;
        node = (
          <a
            key={key}
            href={href}
            target={target ?? undefined}
            rel={!isInternal ? "noopener noreferrer" : undefined}
            className="text-cyan-glow underline underline-offset-2 hover:text-foreground"
          >
            {node}
          </a>
        );
        break;
      }
      default:
        break;
    }
  }
  return node;
}

function headingId(text: string, used: Map<string, number>): string {
  const base = slugify(text) || "seccion";
  const count = used.get(base) ?? 0;
  used.set(base, count + 1);
  return count === 0 ? base : `${base}-${count + 1}`;
}

function renderChildren(nodes: JSONContent[] | undefined, ctx: RenderCtx): ReactNode[] {
  return (nodes ?? []).map((node, i) => <Fragment key={i}>{renderNode(node, ctx)}</Fragment>);
}

interface RenderCtx {
  products: Record<string, BlogDealSummary>;
  headingIds: Map<string, number>;
}

function renderNode(node: JSONContent, ctx: RenderCtx): ReactNode {
  switch (node.type) {
    case "doc":
      return renderChildren(node.content, ctx);
    case "paragraph": {
      const align = node.attrs?.textAlign as string | undefined;
      return (
        <p style={align ? { textAlign: align as "left" | "center" | "right" } : undefined}>
          {renderChildren(node.content, ctx)}
        </p>
      );
    }
    case "text":
      return renderMarks(node.text ?? "", node.marks, node.text ?? "");
    case "hardBreak":
      return <br />;
    case "heading": {
      const level = (node.attrs?.level as number) ?? 2;
      const text = (node.content ?? [])
        .filter((c) => c.type === "text")
        .map((c) => c.text ?? "")
        .join("");
      const id = level <= 3 ? headingId(text, ctx.headingIds) : undefined;
      const Tag = `h${level}` as unknown as "h2" | "h3" | "h4";
      return <Tag id={id}>{renderChildren(node.content, ctx)}</Tag>;
    }
    case "bulletList":
      return <ul>{renderChildren(node.content, ctx)}</ul>;
    case "orderedList":
      return <ol>{renderChildren(node.content, ctx)}</ol>;
    case "listItem":
      return <li>{renderChildren(node.content, ctx)}</li>;
    case "taskList":
      return <ul className="not-prose list-none pl-0">{renderChildren(node.content, ctx)}</ul>;
    case "taskItem":
      return (
        <li className="flex items-start gap-2">
          <input type="checkbox" checked={!!node.attrs?.checked} readOnly className="mt-1.5" />
          <span>{renderChildren(node.content, ctx)}</span>
        </li>
      );
    case "blockquote":
      return <blockquote>{renderChildren(node.content, ctx)}</blockquote>;
    case "codeBlock":
      return (
        <pre className="overflow-x-auto">
          <code>{(node.content ?? []).map((c) => c.text ?? "").join("")}</code>
        </pre>
      );
    case "horizontalRule":
      return <hr />;
    case "image": {
      const align = (node.attrs?.align as string) ?? "left";
      const width = (node.attrs?.width as string) ?? "normal";
      const horizontalMargins =
        align === "center"
          ? { marginLeft: "auto", marginRight: "auto" }
          : align === "right"
            ? { marginLeft: "auto", marginRight: 0 }
            : { marginLeft: 0, marginRight: "auto" };
      return (
        <img
          src={node.attrs?.src}
          alt={node.attrs?.alt ?? ""}
          loading="lazy"
          className={width === "full" ? "w-full" : "max-w-md"}
          style={{
            ...horizontalMargins,
            display: "block",
          }}
        />
      );
    }
    case "table":
      return (
        <div className="overflow-x-auto not-prose my-4">
          <table className="w-full border-collapse border border-surface-700 text-sm">
            <tbody>{renderChildren(node.content, ctx)}</tbody>
          </table>
        </div>
      );
    case "tableRow":
      return <tr>{renderChildren(node.content, ctx)}</tr>;
    case "tableHeader":
      return (
        <th className="border border-surface-700 px-2 py-1.5 bg-surface-800 text-left">
          {renderChildren(node.content, ctx)}
        </th>
      );
    case "tableCell":
      return (
        <td className="border border-surface-700 px-2 py-1.5">
          {renderChildren(node.content, ctx)}
        </td>
      );
    case "callout": {
      const variant = (node.attrs?.variant as string) ?? "info";
      const style = CALLOUT_STYLES[variant] ?? CALLOUT_STYLES.info;
      return (
        <div
          className="not-prose my-4 border-l-4 rounded-r px-4 py-3 bg-surface-800/60"
          style={{ borderColor: style!.border }}
          role="note"
          aria-label={style!.label}
        >
          <p
            className="text-[10px] font-mono uppercase tracking-wide mb-1"
            style={{ color: style!.border }}
          >
            {style!.label}
          </p>
          {renderChildren(node.content, ctx)}
        </div>
      );
    }
    case "productRecommendation": {
      const attrs = node.attrs as {
        mode: "deal" | "manual";
        deal_id: string | null;
        name: string | null;
        image_url: string | null;
        affiliate_url: string | null;
        note: string | null;
        button_text: string | null;
        badge: string | null;
      };
      const deal = attrs.deal_id ? ctx.products[attrs.deal_id] : undefined;
      return <ProductRecommendationCard attrs={attrs} deal={deal} />;
    }
    default:
      return null;
  }
}

export function ContentRenderer({
  doc,
  products,
}: {
  doc: JSONContent;
  products?: Record<string, BlogDealSummary>;
}) {
  const ctx: RenderCtx = { products: products ?? {}, headingIds: new Map() };
  return <>{renderNode(doc, ctx)}</>;
}
