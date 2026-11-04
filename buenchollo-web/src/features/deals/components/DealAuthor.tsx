import { useState } from "react";
import type { DealAuthor as DealAuthorData } from "@/services/api/submissions";

interface DealAuthorProps {
  author: DealAuthorData | null | undefined;
  size?: "sm" | "md";
}

export function DealAuthor({ author, size = "md" }: DealAuthorProps) {
  const [brokenUrl, setBrokenUrl] = useState<string | null>(null);
  if (!author) return null;
  const broken = brokenUrl !== null && brokenUrl === author.avatar_url;

  const name = author.display_name || author.username || "la comunidad";
  const sm = size === "sm";
  const boxCls = sm ? "size-5 text-[10px]" : "size-8 text-sm";

  return (
    <div
      className={`deal-author flex items-center min-w-0 ${sm ? "gap-1.5 text-xs" : "gap-2 text-sm"} text-muted-foreground`}
    >
      {author.avatar_url && !broken ? (
        <img
          src={author.avatar_url}
          alt=""
          referrerPolicy="no-referrer"
          loading="lazy"
          onError={() => setBrokenUrl(author.avatar_url)}
          className={`${boxCls} shrink-0 rounded-full object-cover`}
        />
      ) : (
        <span
          aria-hidden="true"
          data-testid="author-initial"
          className={`${boxCls} shrink-0 rounded-full bg-surface-700 text-foreground font-mono font-bold inline-flex items-center justify-center uppercase`}
        >
          {name.charAt(0)}
        </span>
      )}
      <span className="min-w-0 truncate">
        Compartido por <strong className="text-foreground font-semibold">{name}</strong>
      </span>
    </div>
  );
}
