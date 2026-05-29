import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Layout } from "@/components/Layout";
import { useAuth } from "@/hooks/useAuth";
import { alertsApi } from "@/services/api/alerts";
import { categoriesService, type Category } from "@/services/api/categories";
import { storesService, type Store } from "@/services/api/stores";
import { toast } from "sonner";
import {
  BellRing,
  ChevronDown,
  ChevronUp,
  Flame,
  Plus,
  Search,
  Store as StoreIcon,
  Tag,
} from "lucide-react";
import { alertFormSchema } from "@/lib/validation/alerts";
import { errorMessage } from "@/lib/errors";

const KEYWORD_SUGGESTIONS = [
  "consola ps5",
  "iphone",
  "nintendo switch 2",
  "rtx 5090",
  "macbook air",
  "ssd 2tb",
  "monitor 4k",
  "airpods pro",
  "tv oled",
  "steam deck",
  "portatil gaming",
];

export const Route = createFileRoute("/alertas_/nueva")({
  component: NewAlertPage,
  head: () => ({
    meta: [
      { title: "Nueva alerta · BuencholloTech" },
      {
        name: "description",
        content:
          "Crea una alerta para recibir avisos cuando aparezcan chollos de tus productos favoritos.",
      },
      { property: "og:title", content: "Nueva alerta · BuencholloTech" },
      { name: "robots", content: "noindex, nofollow" },
    ],
  }),
});

function NewAlertPage() {
  const { user, loading: authLoading } = useAuth();
  const nav = useNavigate();
  const [cats, setCats] = useState<Category[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [keyword, setKeyword] = useState("");
  const [selectedCat, setSelectedCat] = useState("");
  const [selectedStore, setSelectedStore] = useState("");
  const [brand, setBrand] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [minDiscount, setMinDiscount] = useState("");

  useEffect(() => {
    if (!authLoading && !user) nav({ to: "/login" });
  }, [authLoading, user, nav]);

  useEffect(() => {
    Promise.all([categoriesService.getAll(), storesService.getAll()])
      .then(([c, s]) => {
        setCats(c.filter((cat) => !cat.parent_id));
        setStores(s.filter((st) => st.is_active));
      })
      .catch(() => toast.error("No se pudieron cargar los filtros"));
  }, []);

  const selectedCatName = useMemo(
    () => cats.find((c) => c.id === selectedCat)?.name,
    [cats, selectedCat],
  );
  const selectedStoreName = useMemo(
    () => stores.find((s) => s.id === selectedStore)?.name,
    [stores, selectedStore],
  );

  const applySuggestion = (value: string) => setKeyword(value);

  const applyHotDeals = () => {
    setKeyword("");
    setSelectedCat("");
    setSelectedStore("");
    setBrand("");
    setMaxPrice("");
    setMinDiscount("30");
  };

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!user) return;

    const parsed = alertFormSchema.safeParse({
      keyword,
      category_id: selectedCat,
      store_id: selectedStore,
      brand,
      max_price: maxPrice,
      min_discount: minDiscount,
    });
    if (!parsed.success) {
      toast.error(parsed.error.issues[0]?.message ?? "Datos inválidos");
      return;
    }
    const data = parsed.data;

    setSubmitting(true);
    try {
      const name =
        data.keyword ||
        selectedCatName ||
        selectedStoreName ||
        data.brand ||
        "Ofertas super calientes";
      await alertsApi.create({
        name,
        keyword: data.keyword,
        category_id: data.category_id,
        store_id: data.store_id,
        brand: data.brand,
        min_price: null,
        max_price: data.max_price,
        min_discount: data.min_discount,
      });
      toast.success("Alerta creada. Te avisaremos en la campana cuando haya coincidencias.");
      nav({ to: "/alertas" });
    } catch (error: unknown) {
      toast.error(errorMessage(error, "No se pudo crear la alerta"));
    } finally {
      setSubmitting(false);
    }
  };

  const hasPreview =
    keyword || selectedCatName || selectedStoreName || brand || maxPrice || minDiscount;
  const inputCls =
    "w-full bg-surface-900 border border-surface-700 px-3 py-2.5 font-mono text-sm outline-none focus:border-cyan-glow transition-colors";

  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
        <Link
          to="/alertas"
          className="font-mono text-xs text-muted-foreground hover:text-cyan-glow transition-colors"
        >
          &lt; MIS ALERTAS
        </Link>

        <section className="mt-8">
          <div className="flex items-center gap-3 mb-5">
            <div className="size-11 border border-cyan-glow/50 bg-cyan-glow/10 flex items-center justify-center">
              <BellRing className="size-5 text-cyan-glow" />
            </div>
            <div className="font-mono text-xs text-cyan-glow uppercase tracking-widest">
              &gt; RADAR_ALERTAS
            </div>
          </div>

          <h1 className="text-3xl sm:text-5xl font-bold tracking-tighter leading-tight mb-3">
            No te pierdas ninguna oferta
          </h1>
          <p className="text-base sm:text-xl text-foreground/90 max-w-2xl leading-relaxed">
            Crea una alerta para que te avisemos de grandes chollos en tus productos favoritos.
          </p>
        </section>

        <form onSubmit={submit} className="mt-7 space-y-7">
          <div className="flex items-center bg-surface-800 border border-surface-600 focus-within:border-cyan-glow transition-colors">
            <span className="pl-4 text-muted-foreground shrink-0">
              <Plus className="size-5" />
            </span>
            <input
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="Crea tu alerta"
              className="flex-1 bg-transparent px-3 py-4 text-base outline-none text-foreground placeholder:text-muted-foreground"
              aria-label="Producto o palabra clave"
              autoFocus
            />
            <button
              type="submit"
              disabled={submitting}
              aria-label="Crear alerta"
              className="mr-2 p-2 text-cyan-glow hover:text-foreground disabled:opacity-50 transition-colors"
            >
              <Search className="size-5" />
            </button>
          </div>

          <div>
            <p className="font-bold text-sm mb-3">Un poco de inspiracion</p>
            <div className="flex flex-wrap gap-2">
              {KEYWORD_SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => applySuggestion(suggestion)}
                  className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-sm font-bold transition-colors ${
                    keyword === suggestion
                      ? "border-cyan-glow text-cyan-glow bg-cyan-glow/10"
                      : "border-surface-600 text-foreground hover:border-cyan-glow hover:text-cyan-glow"
                  }`}
                >
                  <BellRing className="size-4" />
                  {suggestion}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 text-center">
            <div className="h-px bg-surface-700" />
            <p className="font-bold text-sm">No te decides?</p>
            <div className="h-px bg-surface-700" />
          </div>

          <div>
            <p className="text-sm text-muted-foreground mb-3">
              Descubre las mejores elecciones de la comunidad
            </p>
            <button
              type="button"
              onClick={applyHotDeals}
              className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-sm font-bold transition-colors ${
                minDiscount === "30" && !keyword
                  ? "border-cyan-glow text-cyan-glow bg-cyan-glow/10"
                  : "border-surface-600 hover:border-cyan-glow hover:text-cyan-glow"
              }`}
            >
              <Flame className="size-4" />
              Ofertas super calientes
            </button>
          </div>

          <div className="border border-surface-700">
            <button
              type="button"
              onClick={() => setShowAdvanced((v) => !v)}
              className="w-full flex items-center justify-between px-4 py-3 font-mono text-xs uppercase text-muted-foreground hover:text-foreground transition-colors"
            >
              <span>Afina tu alerta</span>
              {showAdvanced ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
            </button>

            {showAdvanced && (
              <div className="px-4 pb-4 space-y-4 border-t border-surface-700 pt-4">
                {cats.length > 0 && (
                  <div>
                    <label className="flex items-center gap-2 font-mono text-[10px] uppercase text-cyan-glow mb-2">
                      <Tag className="size-3" />
                      Categoria
                    </label>
                    <select
                      value={selectedCat}
                      onChange={(e) => setSelectedCat(e.target.value)}
                      className={inputCls}
                    >
                      <option value="">Cualquiera</option>
                      {cats.map((cat) => (
                        <option key={cat.id} value={cat.id}>
                          {cat.name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="flex items-center gap-2 font-mono text-[10px] uppercase text-cyan-glow mb-2">
                      <StoreIcon className="size-3" />
                      Tienda
                    </label>
                    <select
                      value={selectedStore}
                      onChange={(e) => setSelectedStore(e.target.value)}
                      className={inputCls}
                    >
                      <option value="">Cualquiera</option>
                      {stores.map((store) => (
                        <option key={store.id} value={store.id}>
                          {store.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block font-mono text-[10px] uppercase text-cyan-glow mb-2">
                      Marca
                    </label>
                    <input
                      value={brand}
                      onChange={(e) => setBrand(e.target.value)}
                      className={inputCls}
                      placeholder="Apple, Sony, Samsung..."
                    />
                  </div>
                </div>

                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block font-mono text-[10px] uppercase text-cyan-glow mb-2">
                      Precio maximo
                    </label>
                    <input
                      type="number"
                      min="0"
                      value={maxPrice}
                      onChange={(e) => setMaxPrice(e.target.value)}
                      className={inputCls}
                      placeholder="sin limite"
                    />
                  </div>
                  <div>
                    <label className="block font-mono text-[10px] uppercase text-cyan-glow mb-2">
                      Descuento minimo
                    </label>
                    <div className="grid grid-cols-4 gap-2">
                      {[10, 20, 30, 50].map((value) => (
                        <button
                          key={value}
                          type="button"
                          onClick={() =>
                            setMinDiscount(minDiscount === String(value) ? "" : String(value))
                          }
                          className={`font-mono text-xs px-2 py-2 border transition-colors ${
                            minDiscount === String(value)
                              ? "border-cyan-glow text-cyan-glow bg-cyan-glow/10"
                              : "border-surface-700 hover:border-surface-500"
                          }`}
                        >
                          -{value}%
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {hasPreview && (
            <div className="bg-surface-800 border-l-2 border-cyan-glow px-4 py-3 text-sm text-muted-foreground">
              <span className="font-mono text-cyan-glow uppercase">Radar: </span>
              {keyword && <span>"{keyword}" </span>}
              {selectedCatName && <span>· {selectedCatName} </span>}
              {selectedStoreName && <span>· {selectedStoreName} </span>}
              {brand && <span>· {brand} </span>}
              {maxPrice && <span>· hasta {maxPrice} EUR </span>}
              {minDiscount && <span>· -{minDiscount}% o mas </span>}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="bg-cyan-glow text-surface-900 font-bold px-6 py-3 hover:bg-foreground transition-colors disabled:opacity-50"
          >
            {submitting ? "Creando..." : "Crear alerta"}
          </button>
        </form>
      </div>
    </Layout>
  );
}
