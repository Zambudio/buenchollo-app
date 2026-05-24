import { Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  X, Sparkles, TrendingUp, Clock, Percent, Send,
  Smartphone, Laptop, Headphones, Tv, Gamepad2, Cpu, Home as HomeIcon,
  Watch, HardDrive, Keyboard, Camera, Router, Zap,
} from "lucide-react";
import { categoriesService, type Category } from "@/services/api/categories";
import { storesService, type Store } from "@/services/api/stores";

const ICONS: Record<string, any> = {
  smartphone: Smartphone, laptop: Laptop, headphones: Headphones, tv: Tv,
  gamepad: Gamepad2, cpu: Cpu, home: HomeIcon, watch: Watch,
  storage: HardDrive, keyboard: Keyboard, camera: Camera, router: Router, energy: Zap,
};

const TELEGRAM_URL = "https://t.me/buenchollotech";

interface Props {
  readonly open: boolean;
  readonly onClose: () => void;
}

export function CategoriesDrawer({ open, onClose }: Props) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!open || loaded) return;
    Promise.all([categoriesService.getWithDeals(), storesService.getWithDeals()])
      .then(([cats, sts]) => {
        setCategories(cats);
        setStores(sts);
        setLoaded(true);
      })
      .catch(console.error);
  }, [open, loaded]);

  const itemCls = "flex items-center gap-3 px-3 py-2.5 text-sm text-foreground rounded hover:bg-surface-700 hover:text-cyan-glow transition-colors";

  return (
    <>
      {/* Overlay */}
      <div
        className={`fixed inset-0 z-40 bg-black/60 transition-opacity duration-300 ${open ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"}`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <dialog
        aria-label="Menú de categorías"
        open={open}
        className={`fixed left-0 top-0 z-50 h-full w-72 m-0 p-0 bg-surface-800 border-r border-surface-600 flex flex-col shadow-2xl transform transition-transform duration-300 ease-in-out max-h-none ${open ? "translate-x-0" : "-translate-x-full"}`}
      >
        {/* Cabecera */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-surface-600 bg-surface-900 shrink-0">
          <span className="font-mono text-xs font-bold text-cyan-glow uppercase tracking-widest">&gt; MENÚ</span>
          <button type="button" onClick={onClose} aria-label="Cerrar menú"
            className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-surface-700 rounded transition-colors">
            <X className="size-4" />
          </button>
        </div>

        {/* Contenido scrollable */}
        <div className="flex-1 overflow-y-auto py-2">

          {/* TENDENCIAS */}
          <div className="px-3 pt-3 pb-1">
            <p className="px-3 font-mono text-[10px] font-semibold text-muted-foreground uppercase tracking-widest mb-1">Tendencias</p>
            <nav className="flex flex-col">
              <Link to="/explorar" search={{ sort: "popular" } as any} onClick={onClose} className={itemCls}>
                <TrendingUp className="size-4 text-cyan-glow shrink-0" />
                <span>Más populares</span>
              </Link>
              <Link to="/explorar" search={{ sort: "recent" } as any} onClick={onClose} className={itemCls}>
                <Clock className="size-4 text-cyan-glow shrink-0" />
                <span>Nuevos chollos</span>
              </Link>
              <Link to="/explorar" search={{ sort: "discount" } as any} onClick={onClose} className={itemCls}>
                <Percent className="size-4 text-cyan-glow shrink-0" />
                <span>Mayor descuento</span>
              </Link>
            </nav>
          </div>

          <div className="mx-4 my-2 border-t border-surface-600" />

          {/* CATEGORÍAS */}
          <div className="px-3 pb-1">
            <p className="px-3 font-mono text-[10px] font-semibold text-muted-foreground uppercase tracking-widest mb-1">Categorías</p>
            <nav className="flex flex-col">
              {categories.map(c => {
                const Icon = (c.icon ? ICONS[c.icon] : null) ?? Sparkles;
                return (
                  <Link key={c.id} to="/categoria/$slug" params={{ slug: c.slug }} onClick={onClose} className={itemCls}>
                    <Icon className="size-4 text-cyan-glow shrink-0" />
                    <span>{c.name}</span>
                  </Link>
                );
              })}
              <Link to="/categorias" onClick={onClose}
                className="px-3 py-2 text-xs text-muted-foreground hover:text-cyan-glow transition-colors mt-1">
                Ver todas las categorías →
              </Link>
            </nav>
          </div>

          {stores.length > 0 && (
            <>
              <div className="mx-4 my-2 border-t border-surface-600" />

              {/* TIENDAS */}
              <div className="px-3 pb-1">
                <p className="px-3 font-mono text-[10px] font-semibold text-muted-foreground uppercase tracking-widest mb-2">Tiendas</p>
                <div className="flex flex-wrap gap-2 px-3">
                  {stores.map(s => (
                    <Link
                      key={s.id}
                      to="/explorar"
                      search={{ store: s.id } as any}
                      onClick={onClose}
                      className="text-sm text-foreground px-3 py-1.5 border border-surface-600 bg-surface-900 hover:border-cyan-glow hover:text-cyan-glow transition-colors rounded"
                    >
                      {s.name}
                    </Link>
                  ))}
                </div>
              </div>
            </>
          )}

          <div className="mx-4 my-2 border-t border-surface-600" />

          {/* TELEGRAM */}
          <div className="px-3 pb-3">
            <a href={TELEGRAM_URL} target="_blank" rel="noopener noreferrer" onClick={onClose} className={itemCls}>
              <Send className="size-4 text-cyan-glow shrink-0" />
              <span>Canal de Telegram</span>
            </a>
          </div>
        </div>
      </dialog>
    </>
  );
}
