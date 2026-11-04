import { Link } from "@tanstack/react-router";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { loginSearch } from "@/lib/safe-redirect";

interface AuthRequiredDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  redirectTo?: string;
}

export function AuthRequiredDialog({
  open,
  onOpenChange,
  redirectTo = "/publicar",
}: AuthRequiredDialogProps) {
  const search = loginSearch(redirectTo);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Comparte un chollo</DialogTitle>
          <DialogDescription>
            Para compartir chollos con la comunidad necesitas una cuenta.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2 pt-2">
          <Link
            to="/registro"
            search={search}
            className="w-full text-center bg-cyan-glow text-surface-900 font-mono text-xs font-bold py-3 hover:bg-foreground transition-colors"
          >
            Crear cuenta
          </Link>
          <Link
            to="/login"
            search={search}
            className="w-full text-center border border-surface-600 bg-surface-900 text-foreground font-mono text-xs font-bold py-3 hover:border-cyan-glow transition-colors"
          >
            Iniciar sesión
          </Link>
        </div>
      </DialogContent>
    </Dialog>
  );
}
