import { Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import {
  Search,
  Bell,
  Heart,
  User as UserIcon,
  LogOut,
  Shield,
  Menu,
  X,
  LayoutGrid,
  BellPlus,
} from "lucide-react";
import { Logo } from "./Logo";
import { useAuth } from "@/hooks/useAuth";
import { useUnreadNotifications } from "@/features/notifications/hooks/useNotifications";
import { CategoriesDrawer } from "./CategoriesDrawer";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function Header() {
  const { user, isAdmin, signOut } = useAuth();
  const [q, setQ] = useState("");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const nav = useNavigate();
  const { data: unread = 0 } = useUnreadNotifications();

  const onSearch = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    nav({ to: "/explorar", search: { q: q.trim() || undefined } });
  };

  return (
    <>
      <CategoriesDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
      <header className="border-b border-surface-700 bg-surface-900/95 sticky top-0 z-50 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              aria-label="Abrir menú de categorías"
              className="p-2 border border-surface-600 text-foreground hover:border-cyan-glow hover:text-cyan-glow transition-colors"
            >
              <LayoutGrid className="size-5" />
            </button>
            <Link to="/">
              <Logo />
            </Link>
          </div>

          <form onSubmit={onSearch} className="hidden md:flex flex-1 max-w-md">
            <div className="w-full flex items-center bg-surface-800 border border-surface-700 px-3 py-1.5 focus-within:border-cyan-glow focus-within:glow-cyan transition-all">
              <span className="text-cyan-glow font-mono mr-2 text-sm">&gt;</span>
              <label htmlFor="header-search" className="sr-only">
                Buscar chollo
              </label>
              <input
                id="header-search"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                type="text"
                placeholder="BUSCAR_CHOLLO..."
                className="bg-transparent border-none outline-none w-full text-sm font-mono placeholder:text-muted-foreground text-foreground uppercase"
              />
              <button
                type="submit"
                aria-label="Buscar"
                className="text-cyan-glow hover:text-foreground transition-colors"
              >
                <Search className="size-4" />
              </button>
            </div>
          </form>

          <div className="flex items-center gap-2 sm:gap-4">
            {user ? (
              <>
                <Link
                  to="/notificaciones"
                  className="relative p-2 hover:text-cyan-glow transition-colors"
                  title="Notificaciones"
                >
                  <Bell className="size-5" />
                  {unread > 0 && (
                    <span className="absolute -top-0.5 -right-0.5 bg-alert-red text-white text-[10px] font-mono font-bold rounded-full size-4 flex items-center justify-center">
                      {unread > 9 ? "9+" : unread}
                    </span>
                  )}
                </Link>
                <Link
                  to="/favoritos"
                  className="hidden sm:block p-2 hover:text-cyan-glow transition-colors"
                  title="Favoritos"
                >
                  <Heart className="size-5" />
                </Link>
                <Link
                  to="/alertas/nueva"
                  className="hidden sm:block p-2 hover:text-cyan-glow transition-colors"
                  title="Crear alerta"
                >
                  <BellPlus className="size-5" />
                </Link>
                <DropdownMenu>
                  <DropdownMenuTrigger
                    aria-label="Menú de perfil"
                    className="size-9 rounded-full bg-surface-700 border border-surface-600 flex items-center justify-center hover:border-cyan-glow transition-colors"
                  >
                    <UserIcon className="size-4" />
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-52">
                    <DropdownMenuItem asChild>
                      <Link to="/perfil">Mi perfil</Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem asChild>
                      <Link to="/favoritos">Favoritos</Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem asChild>
                      <Link to="/alertas">Alertas</Link>
                    </DropdownMenuItem>
                    {isAdmin && (
                      <>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem asChild>
                          <Link to="/admin">
                            <Shield className="size-4 mr-2" />
                            Panel admin
                          </Link>
                        </DropdownMenuItem>
                      </>
                    )}
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={signOut} className="text-alert-red">
                      <LogOut className="size-4 mr-2" />
                      Cerrar sesión
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            ) : (
              <Link
                to="/login"
                className="font-mono text-xs sm:text-sm hover:text-cyan-glow transition-colors whitespace-nowrap"
              >
                [ ACCEDER ]
              </Link>
            )}
            <button
              type="button"
              className="md:hidden p-2"
              aria-label={mobileOpen ? "Cerrar menú" : "Abrir menú"}
              aria-expanded={mobileOpen}
              onClick={() => setMobileOpen((v) => !v)}
            >
              {mobileOpen ? <X className="size-5" /> : <Menu className="size-5" />}
            </button>
          </div>
        </div>

        {mobileOpen && (
          <div className="md:hidden border-t border-surface-700 px-4 py-4 space-y-3 bg-surface-800">
            <form
              onSubmit={onSearch}
              className="flex items-center bg-surface-900 border border-surface-700 px-3 py-2"
            >
              <span className="text-cyan-glow font-mono mr-2 text-sm">&gt;</span>
              <label htmlFor="header-search-mobile" className="sr-only">
                Buscar chollo
              </label>
              <input
                id="header-search-mobile"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="BUSCAR..."
                className="bg-transparent outline-none w-full text-sm font-mono uppercase"
              />
            </form>
            <Link
              to="/explorar"
              className="block font-mono text-sm hover:text-cyan-glow"
              onClick={() => setMobileOpen(false)}
            >
              [ EXPLORAR ]
            </Link>
            <Link
              to="/categorias"
              className="block font-mono text-sm hover:text-cyan-glow"
              onClick={() => setMobileOpen(false)}
            >
              [ CATEGORÍAS ]
            </Link>
            {user && (
              <Link
                to="/alertas"
                className="block font-mono text-sm hover:text-cyan-glow"
                onClick={() => setMobileOpen(false)}
              >
                [ ALERTAS ]
              </Link>
            )}
          </div>
        )}
      </header>
    </>
  );
}
