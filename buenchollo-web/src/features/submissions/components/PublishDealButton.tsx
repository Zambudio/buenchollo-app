import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { Plus } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { AuthRequiredDialog } from "./AuthRequiredDialog";

interface PublishDealButtonProps {
  variant?: "header" | "menu" | "cta";
  onNavigate?: () => void;
}

export function PublishDealButton({ variant = "header", onNavigate }: PublishDealButtonProps) {
  const { user } = useAuth();
  const [dialogOpen, setDialogOpen] = useState(false);

  const isMenu = variant === "menu";
  const isCta = variant === "cta";
  const className = isCta
    ? "inline-flex items-center justify-center gap-1.5 px-5 py-2.5 rounded-full bg-cyan-glow text-surface-900 font-mono text-sm font-bold hover:bg-foreground transition-colors"
    : isMenu
      ? "flex items-center gap-2 font-mono text-sm text-cyan-glow hover:text-foreground"
      : "inline-flex items-center justify-center gap-1.5 shrink-0 size-9 md:size-auto md:px-4 md:py-1.5 rounded-full bg-cyan-glow text-surface-900 font-mono text-xs md:text-sm font-bold hover:bg-foreground transition-colors";
  const content = (
    <>
      <Plus className="size-4" aria-hidden="true" />
      <span className={isMenu || isCta ? "" : "hidden md:inline whitespace-nowrap"}>
        {isMenu ? "PUBLICAR CHOLLO" : "Publicar chollo"}
      </span>
    </>
  );

  return (
    <>
      {user ? (
        <Link
          to="/publicar"
          aria-label={isMenu || isCta ? undefined : "Publicar chollo"}
          className={className}
          onClick={onNavigate}
        >
          {content}
        </Link>
      ) : (
        <button
          type="button"
          aria-label={isMenu || isCta ? undefined : "Publicar chollo"}
          className={className}
          onClick={() => setDialogOpen(true)}
        >
          {content}
        </button>
      )}
      {!user && <AuthRequiredDialog open={dialogOpen} onOpenChange={setDialogOpen} />}
    </>
  );
}
