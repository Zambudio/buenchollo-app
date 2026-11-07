import { useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { currentPageLoginSearch } from "@/lib/safe-redirect";

/** Manda a `/login` a quien entra sin sesión en una página privada y conserva
 *  la página actual en `?redirect=` para volver a ella tras iniciar sesión. */
export function useRequireLogin(): void {
  const { user, loading } = useAuth();
  const nav = useNavigate();

  useEffect(() => {
    if (!loading && !user) {
      nav({ to: "/login", search: currentPageLoginSearch(), replace: true });
    }
  }, [loading, user, nav]);
}
