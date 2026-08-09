import { useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Camera,
  Headphones,
  Tv,
  Monitor,
  Smartphone,
  Laptop,
  Gamepad2,
  Cpu,
  Zap,
  Watch,
  Store as StoreIcon,
  Tag,
  Plus,
  Check,
  Bell,
  Keyboard,
  Mouse,
  HardDrive,
  Cable,
  ShoppingBag,
  SlidersHorizontal,
} from "lucide-react";
import { alertsApi, type AlertCreate } from "@/services/api/alerts";
import { useAuth } from "@/hooks/useAuth";
import type { DealDetailData } from "@/services/api/deals";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface RecommendedAlertsBlockProps {
  deal: DealDetailData;
  className?: string;
}

interface AlertCandidate {
  id: string;
  name: string;
  type: "keyword" | "brand" | "category" | "store";
  keyword?: string;
  brand?: string;
  category_id?: string;
  store_id?: string;
  iconType: string;
  imageUrl?: string | null;
  accentColor?: string;
}

const COMMON_STOPWORDS = new Set([
  "de",
  "del",
  "la",
  "el",
  "los",
  "las",
  "un",
  "una",
  "unos",
  "unas",
  "con",
  "para",
  "por",
  "en",
  "y",
  "o",
  "a",
  "al",
  "sin",
  "sobre",
  "tras",
  "mas",
  "más",
  "nuevo",
  "reacondicionado",
  "como",
  "oferta",
  "chollo",
  "pack",
  "combo",
]);

const STORE_LOGOS: Record<string, string> = {
  amazon: "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg",
  aliexpress: "https://upload.wikimedia.org/wikipedia/commons/3/3b/Aliexpress_logo.svg",
  pccomponentes:
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Logo_de_PcComponentes.svg/320px-Logo_de_PcComponentes.svg.png",
  mediamarkt: "https://upload.wikimedia.org/wikipedia/commons/e/ee/Media_Markt_logo.svg",
  "el corte inglés":
    "https://upload.wikimedia.org/wikipedia/commons/4/4e/El_Corte_Ingl%C3%A9s_logo.svg",
  "el corte ingles":
    "https://upload.wikimedia.org/wikipedia/commons/4/4e/El_Corte_Ingl%C3%A9s_logo.svg",
  miravia: "https://upload.wikimedia.org/wikipedia/commons/6/66/Miravia_Logo.svg",
  carrefour: "https://upload.wikimedia.org/wikipedia/commons/5/5b/Carrefour_logo.svg",
  zalando: "https://upload.wikimedia.org/wikipedia/commons/1/1e/Zalando_logo.svg",
  apple: "https://upload.wikimedia.org/wikipedia/commons/f/fa/Apple_logo_black.svg",
};

const BRAND_LOGOS: Record<string, string> = {
  apple: "https://upload.wikimedia.org/wikipedia/commons/f/fa/Apple_logo_black.svg",
  samsung: "https://upload.wikimedia.org/wikipedia/commons/2/24/Samsung_Logo.svg",
  xiaomi: "https://upload.wikimedia.org/wikipedia/commons/a/ae/Xiaomi_logo_%282021-%29.svg",
  sony: "https://upload.wikimedia.org/wikipedia/commons/c/ca/Sony_logo.svg",
  nintendo: "https://upload.wikimedia.org/wikipedia/commons/0/0d/Nintendo.svg",
  asus: "https://upload.wikimedia.org/wikipedia/commons/2/2e/ASUS_Logo.svg",
  logitech: "https://upload.wikimedia.org/wikipedia/commons/1/17/Logitech_logo.svg",
  lg: "https://upload.wikimedia.org/wikipedia/commons/b/bf/LG_logo_%282015%29.svg",
  lenovo: "https://upload.wikimedia.org/wikipedia/commons/b/b8/Lenovo_logo_2015.svg",
  hp: "https://upload.wikimedia.org/wikipedia/commons/a/ad/HP_logo_2012.svg",
  dell: "https://upload.wikimedia.org/wikipedia/commons/4/48/Dell_Logo.svg",
  gopro: "https://upload.wikimedia.org/wikipedia/commons/0/06/GoPro_logo.svg",
  canon: "https://upload.wikimedia.org/wikipedia/commons/8/8d/Canon_logo.svg",
  polaroid: "https://upload.wikimedia.org/wikipedia/commons/2/24/Polaroid_Corporation_logo.svg",
};

function getStoreLogoUrl(storeName?: string | null, storeLogoUrl?: string | null): string | null {
  if (storeLogoUrl) return storeLogoUrl;
  if (!storeName) return null;
  const key = storeName.toLowerCase().trim();
  return STORE_LOGOS[key] || null;
}

function getBrandLogoUrl(brandName?: string | null): string | null {
  if (!brandName) return null;
  const key = brandName.toLowerCase().trim();
  return BRAND_LOGOS[key] || null;
}

function getIconComponent(iconType: string) {
  switch (iconType) {
    case "camera":
      return Camera;
    case "headphones":
      return Headphones;
    case "tv":
      return Tv;
    case "monitor":
      return Monitor;
    case "smartphone":
      return Smartphone;
    case "laptop":
      return Laptop;
    case "gaming":
      return Gamepad2;
    case "cpu":
      return Cpu;
    case "power":
      return Zap;
    case "watch":
      return Watch;
    case "store":
      return StoreIcon;
    case "peripherals":
    case "hub":
      return Cable;
    case "keyboard":
      return Keyboard;
    case "mouse":
      return Mouse;
    case "storage":
      return HardDrive;
    default:
      return Tag;
  }
}

function getIconTheme(iconType: string) {
  switch (iconType) {
    case "camera":
      return {
        bg: "bg-emerald-500/15 dark:bg-emerald-500/20",
        text: "text-emerald-600 dark:text-emerald-400",
      };
    case "headphones":
      return {
        bg: "bg-purple-500/15 dark:bg-purple-500/20",
        text: "text-purple-600 dark:text-purple-400",
      };
    case "tv":
    case "monitor":
      return { bg: "bg-blue-500/15 dark:bg-blue-500/20", text: "text-blue-600 dark:text-blue-400" };
    case "smartphone":
      return { bg: "bg-cyan-500/15 dark:bg-cyan-500/20", text: "text-cyan-600 dark:text-cyan-400" };
    case "laptop":
      return {
        bg: "bg-indigo-500/15 dark:bg-indigo-500/20",
        text: "text-indigo-600 dark:text-indigo-400",
      };
    case "gaming":
      return { bg: "bg-rose-500/15 dark:bg-rose-500/20", text: "text-rose-600 dark:text-rose-400" };
    case "cpu":
    case "storage":
      return {
        bg: "bg-amber-500/15 dark:bg-amber-500/20",
        text: "text-amber-600 dark:text-amber-400",
      };
    case "power":
    case "peripherals":
    case "hub":
      return { bg: "bg-sky-500/15 dark:bg-sky-500/20", text: "text-sky-600 dark:text-sky-400" };
    case "watch":
      return { bg: "bg-teal-500/15 dark:bg-teal-500/20", text: "text-teal-600 dark:text-teal-400" };
    case "store":
      return {
        bg: "bg-orange-500/15 dark:bg-orange-500/20",
        text: "text-orange-600 dark:text-orange-400",
      };
    default:
      return { bg: "bg-[#156287]/15 dark:bg-sky-500/20", text: "text-[#156287] dark:text-sky-300" };
  }
}

function detectIconType(text: string): string {
  const lower = text.toLowerCase();
  if (
    lower.includes("cámara") ||
    lower.includes("camara") ||
    lower.includes("gopro") ||
    lower.includes("polaroid") ||
    lower.includes("canon") ||
    lower.includes("nikon") ||
    lower.includes("foto")
  ) {
    return "camera";
  }
  if (
    lower.includes("auricular") ||
    lower.includes("airpod") ||
    lower.includes("buds") ||
    lower.includes("headphone") ||
    lower.includes("altavoz") ||
    lower.includes("sonido")
  ) {
    return "headphones";
  }
  if (lower.includes("monitor") || lower.includes("pantalla")) {
    return "monitor";
  }
  if (lower.includes("tv") || lower.includes("oled") || lower.includes("televis")) {
    return "tv";
  }
  if (
    lower.includes("iphone") ||
    lower.includes("smartphone") ||
    lower.includes("móvil") ||
    lower.includes("movil") ||
    lower.includes("galaxy") ||
    lower.includes("pixel")
  ) {
    return "smartphone";
  }
  if (
    lower.includes("macbook") ||
    lower.includes("portátil") ||
    lower.includes("portatil") ||
    lower.includes("laptop") ||
    lower.includes("ipad") ||
    lower.includes("tablet")
  ) {
    return "laptop";
  }
  if (
    lower.includes("ps5") ||
    lower.includes("switch") ||
    lower.includes("nintendo") ||
    lower.includes("xbox") ||
    lower.includes("steam deck") ||
    lower.includes("gaming") ||
    lower.includes("consola")
  ) {
    return "gaming";
  }
  if (
    lower.includes("hub") ||
    lower.includes("revodok") ||
    lower.includes("adaptador") ||
    lower.includes("periférico") ||
    lower.includes("periferico") ||
    lower.includes("cable") ||
    lower.includes("dock")
  ) {
    return "peripherals";
  }
  if (lower.includes("teclado")) return "keyboard";
  if (lower.includes("ratón") || lower.includes("raton") || lower.includes("mouse")) return "mouse";
  if (
    lower.includes("ssd") ||
    lower.includes("disco") ||
    lower.includes("disco duro") ||
    lower.includes("almacenamiento")
  )
    return "storage";
  if (
    lower.includes("rtx") ||
    lower.includes("ram") ||
    lower.includes("ryzen") ||
    lower.includes("intel") ||
    lower.includes("gráfica") ||
    lower.includes("grafica")
  ) {
    return "cpu";
  }
  if (
    lower.includes("cargador") ||
    lower.includes("power bank") ||
    lower.includes("batería") ||
    lower.includes("bateria") ||
    lower.includes("magsafe") ||
    lower.includes("usb")
  ) {
    return "power";
  }
  if (
    lower.includes("reloj") ||
    lower.includes("watch") ||
    lower.includes("smartwatch") ||
    lower.includes("garmin")
  ) {
    return "watch";
  }
  return "tag";
}

function generateCandidates(deal: DealDetailData): AlertCandidate[] {
  const candidates: AlertCandidate[] = [];
  const addedNames = new Set<string>();

  const addCandidate = (item: AlertCandidate) => {
    const key = item.name.toLowerCase().trim();
    if (!key || addedNames.has(key)) return;
    addedNames.add(key);
    candidates.push(item);
  };

  const title = deal.title || "";
  const titleLower = title.toLowerCase();

  // 1. Frases y modelos específicos con foto del producto
  const KNOWN_PHRASES = [
    { phrase: "ugreen revodok", label: "UGREEN Revodok", icon: "hub" },
    { phrase: "revodok", label: "UGREEN Revodok", icon: "hub" },
    { phrase: "cámara instantánea", label: "Cámara instantánea", icon: "camera" },
    { phrase: "camara instantanea", label: "Cámara instantánea", icon: "camera" },
    { phrase: "cámara deportiva", label: "Cámara deportiva", icon: "camera" },
    { phrase: "camara deportiva", label: "Cámara deportiva", icon: "camera" },
    { phrase: "cámara mirrorless", label: "Cámara mirrorless", icon: "camera" },
    { phrase: "auriculares inalámbricos", label: "Auriculares inalámbricos", icon: "headphones" },
    { phrase: "auriculares inalambricos", label: "Auriculares inalámbricos", icon: "headphones" },
    { phrase: "airpods max", label: "AirPods Max", icon: "headphones" },
    { phrase: "airpods pro", label: "AirPods Pro", icon: "headphones" },
    { phrase: "redmi buds", label: "Redmi Buds", icon: "headphones" },
    { phrase: "power bank", label: "Power Bank", icon: "power" },
    { phrase: "cargador usb", label: "Cargador USB", icon: "power" },
    { phrase: "cargador rápido", label: "Cargador rápido", icon: "power" },
    { phrase: "nintendo switch 2", label: "Nintendo Switch 2", icon: "gaming" },
    { phrase: "nintendo switch", label: "Nintendo Switch", icon: "gaming" },
    { phrase: "consola ps5", label: "Consola PS5", icon: "gaming" },
    { phrase: "ps5 pro", label: "PS5 Pro", icon: "gaming" },
    { phrase: "playstation 5", label: "PlayStation 5", icon: "gaming" },
    { phrase: "steam deck", label: "Steam Deck", icon: "gaming" },
    { phrase: "portatil gaming", label: "Portátil Gaming", icon: "laptop" },
    { phrase: "portátil gaming", label: "Portátil Gaming", icon: "laptop" },
    { phrase: "macbook air", label: "MacBook Air", icon: "laptop" },
    { phrase: "macbook pro", label: "MacBook Pro", icon: "laptop" },
    { phrase: "monitor 4k", label: "Monitor 4K", icon: "monitor" },
    { phrase: "tv oled", label: "TV OLED", icon: "tv" },
    { phrase: "smart tv", label: "Smart TV", icon: "tv" },
    { phrase: "ssd 2tb", label: "SSD 2TB", icon: "storage" },
    { phrase: "ssd 1tb", label: "SSD 1TB", icon: "storage" },
    { phrase: "rtx 5090", label: "RTX 5090", icon: "cpu" },
    { phrase: "rtx 5080", label: "RTX 5080", icon: "cpu" },
    { phrase: "rtx 4070", label: "RTX 4070", icon: "cpu" },
    { phrase: "apple watch", label: "Apple Watch", icon: "watch" },
  ];

  let matchedPhrase = false;
  for (const { phrase, label, icon } of KNOWN_PHRASES) {
    if (titleLower.includes(phrase)) {
      addCandidate({
        id: `phrase-${label}`,
        name: label,
        type: "keyword",
        keyword: label,
        iconType: icon,
        imageUrl: deal.image_url,
      });
      matchedPhrase = true;
      break;
    }
  }

  // 2. Si no hubo match específico, extraer modelo/primeras palabras con la foto del producto
  if (!matchedPhrase) {
    const cleanTokens = title
      .replace(/[^\w\s-]/g, " ")
      .split(/\s+/)
      .filter((t) => t.length > 2 && !COMMON_STOPWORDS.has(t.toLowerCase()));

    if (cleanTokens.length > 0) {
      const topWords = cleanTokens.slice(0, 2).join(" ");
      addCandidate({
        id: `token-${topWords}`,
        name: topWords,
        type: "keyword",
        keyword: topWords,
        iconType: detectIconType(topWords),
        imageUrl: deal.image_url,
      });
    }
  }

  // 3. Marca del chollo (con logo de marca o foto del deal)
  const KNOWN_BRANDS = [
    "Apple",
    "Samsung",
    "Xiaomi",
    "Polaroid",
    "GoPro",
    "Sony",
    "Nintendo",
    "Logitech",
    "Anker",
    "UGREEN",
    "Baseus",
    "MSI",
    "Asus",
    "Lenovo",
    "HP",
    "Dell",
    "LG",
    "Philips",
    "Bose",
    "Sennheiser",
    "Garmin",
    "Canon",
    "Razer",
    "Corsair",
  ];

  let detectedBrand = deal.brand || "";
  if (!detectedBrand) {
    for (const b of KNOWN_BRANDS) {
      if (titleLower.includes(b.toLowerCase())) {
        detectedBrand = b;
        break;
      }
    }
  }

  if (detectedBrand) {
    const brandLogo = getBrandLogoUrl(detectedBrand);
    addCandidate({
      id: `brand-${detectedBrand}`,
      name: detectedBrand,
      type: "brand",
      brand: detectedBrand,
      iconType: detectIconType(detectedBrand),
      imageUrl: brandLogo || deal.image_url,
    });
  }

  // 4. Tienda del chollo (con logo oficial de la tienda)
  if (deal.store?.name) {
    const storeLogo = getStoreLogoUrl(deal.store.name);
    addCandidate({
      id: `store-${deal.store.id || deal.store.name}`,
      name: deal.store.name,
      type: "store",
      store_id: deal.store.id,
      iconType: "store",
      imageUrl: storeLogo,
    });
  }

  // 5. Término general / categoría del producto
  const KNOWN_KEYWORDS = [
    { word: "cámara", label: "Cámara", icon: "camera" },
    { word: "camara", label: "Cámara", icon: "camera" },
    { word: "auriculares", label: "Auriculares", icon: "headphones" },
    { word: "airpods", label: "AirPods", icon: "headphones" },
    { word: "cargador", label: "Cargador", icon: "power" },
    { word: "batería", label: "Batería", icon: "power" },
    { word: "bateria", label: "Batería", icon: "power" },
    { word: "iphone", label: "iPhone", icon: "smartphone" },
    { word: "smartphone", label: "Smartphone", icon: "smartphone" },
    { word: "móvil", label: "Móvil", icon: "smartphone" },
    { word: "portátil", label: "Portátil", icon: "laptop" },
    { word: "macbook", label: "MacBook", icon: "laptop" },
    { word: "tablet", label: "Tablet", icon: "laptop" },
    { word: "ipad", label: "iPad", icon: "laptop" },
    { word: "monitor", label: "Monitor", icon: "monitor" },
    { word: "televisor", label: "Televisor", icon: "tv" },
    { word: "teclado", label: "Teclado", icon: "keyboard" },
    { word: "ratón", label: "Ratón", icon: "mouse" },
    { word: "hub", label: "Hub USB", icon: "hub" },
    { word: "consola", label: "Consola", icon: "gaming" },
    { word: "switch", label: "Nintendo Switch", icon: "gaming" },
    { word: "smartwatch", label: "Smartwatch", icon: "watch" },
    { word: "reloj", label: "Reloj inteligente", icon: "watch" },
  ];

  for (const { word, label, icon } of KNOWN_KEYWORDS) {
    if (titleLower.includes(word)) {
      addCandidate({
        id: `kw-${label}`,
        name: label,
        type: "keyword",
        keyword: label,
        iconType: icon,
      });
      break;
    }
  }

  // 6. Categoría o Subcategoría del chollo (ej. Periféricos, Electrónica, Fotografía)
  if (deal.category?.name) {
    addCandidate({
      id: `cat-${deal.category_id || deal.category.name}`,
      name: deal.category.name,
      type: "category",
      category_id: deal.category_id || undefined,
      iconType: detectIconType(deal.category.name),
    });
  }

  // Retornamos máximo 5 sugerencias para dejar espacio a la tarjeta "Otra alerta"
  return candidates.slice(0, 5);
}

function VisualBadge({ candidate }: { candidate: AlertCandidate }) {
  const [imgError, setImgError] = useState(false);
  const Icon = getIconComponent(candidate.iconType);
  const theme = getIconTheme(candidate.iconType);

  if (candidate.imageUrl && !imgError) {
    return (
      <div className="size-16 sm:size-20 rounded-2xl bg-white p-2 shadow-xs border border-surface-200/90 dark:border-surface-700 flex items-center justify-center overflow-hidden my-2.5 transition-transform duration-200 group-hover:scale-105">
        <img
          src={candidate.imageUrl}
          alt={candidate.name}
          onError={() => setImgError(true)}
          className="size-full object-contain"
          loading="lazy"
          decoding="async"
        />
      </div>
    );
  }

  return (
    <div
      className={cn(
        "size-16 sm:size-20 rounded-2xl flex items-center justify-center my-2.5 transition-transform duration-200 group-hover:scale-105 shadow-xs border border-surface-200/60 dark:border-surface-700",
        theme.bg,
        theme.text,
      )}
    >
      <Icon className="size-7 sm:size-8 stroke-[1.8]" />
    </div>
  );
}

export function RecommendedAlertsBlock({ deal, className }: RecommendedAlertsBlockProps) {
  const { user } = useAuth();
  const nav = useNavigate();
  const qc = useQueryClient();

  const candidates = useMemo(() => generateCandidates(deal), [deal]);

  const { data: userAlerts = [] } = useQuery({
    queryKey: ["alerts", "list"],
    queryFn: () => alertsApi.list(),
    enabled: !!user,
    staleTime: 30 * 1000,
  });

  const createAlertMutation = useMutation({
    mutationFn: (data: AlertCreate) => alertsApi.create(data),
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: ["alerts", "list"] });
      toast.success(`Alerta activada para "${variables.name.replace(/^Alerta:\s*/, "")}"`);
    },
    onError: () => {
      toast.error("No se pudo crear la alerta. Inténtalo de nuevo.");
    },
  });

  const deleteAlertMutation = useMutation({
    mutationFn: (id: string) => alertsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts", "list"] });
      toast.info("Alerta desactivada");
    },
    onError: () => {
      toast.error("No se pudo desactivar la alerta.");
    },
  });

  const candidateStatus = useMemo(() => {
    const statusMap = new Map<string, { isActive: boolean; alertId?: string }>();

    for (const c of candidates) {
      const match = userAlerts.find((a) => {
        if (!a.is_active) return false;
        if (c.type === "keyword" && c.keyword) {
          return a.keyword?.toLowerCase().trim() === c.keyword.toLowerCase().trim();
        }
        if (c.type === "brand" && c.brand) {
          return a.brand?.toLowerCase().trim() === c.brand.toLowerCase().trim();
        }
        if (c.type === "category" && c.category_id) {
          return (
            a.category_id === c.category_id ||
            a.category?.name?.toLowerCase() === c.name.toLowerCase()
          );
        }
        if (c.type === "store" && c.store_id) {
          return a.store_id === c.store_id || a.store?.name?.toLowerCase() === c.name.toLowerCase();
        }
        return false;
      });

      if (match) {
        statusMap.set(c.id, { isActive: true, alertId: match.id });
      } else {
        statusMap.set(c.id, { isActive: false });
      }
    }

    return statusMap;
  }, [candidates, userAlerts]);

  const handleToggleCandidate = (c: AlertCandidate) => {
    if (!user) {
      toast.info("Inicia sesión para activar alertas de chollos");
      nav({ to: "/login" });
      return;
    }

    const current = candidateStatus.get(c.id);
    if (current?.isActive && current.alertId) {
      deleteAlertMutation.mutate(current.alertId);
    } else {
      const payload: AlertCreate = {
        name: `Alerta: ${c.name}`,
        keyword: c.type === "keyword" ? c.keyword : null,
        brand: c.type === "brand" ? c.brand : null,
        category_id: c.type === "category" ? c.category_id : null,
        store_id: c.type === "store" ? c.store_id : null,
      };
      createAlertMutation.mutate(payload);
    }
  };

  const handleCustomize = () => {
    const firstKw = candidates.find((c) => c.type === "keyword")?.keyword || deal.brand || "";
    nav({
      to: "/alertas/nueva",
      search: firstKw ? { keyword: firstKw } : undefined,
    });
  };

  return (
    <section
      aria-label="Alertas recomendadas"
      className={cn(
        "my-8 rounded-2xl border border-surface-700 bg-surface-800 p-5 sm:p-6 shadow-sm transition-all",
        className,
      )}
    >
      {/* Cabecera del bloque */}
      <div className="mb-5">
        <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground font-sans">
          ¡No te pierdas ningún chollo así!
        </h2>
        <p className="text-xs sm:text-sm text-muted-foreground mt-1">
          Te avisamos en cuanto se publique uno parecido. Sin spam.
        </p>
      </div>

      {/* Fila de tarjetas recomendadas */}
      <div className="flex items-stretch gap-3.5 sm:gap-4 overflow-x-auto pb-2 scrollbar-thin">
        {candidates.map((c) => {
          const status = candidateStatus.get(c.id);
          const isActive = status?.isActive || false;
          const isPending = createAlertMutation.isPending || deleteAlertMutation.isPending;

          return (
            <div
              key={c.id}
              className={cn(
                "group w-[142px] sm:w-[160px] shrink-0 rounded-2xl border p-3.5 sm:p-4 flex flex-col items-center justify-between text-center transition-all duration-200 shadow-xs hover:shadow-md",
                isActive
                  ? "border-[#156287]/60 dark:border-sky-400/50 bg-[#156287]/[0.08] dark:bg-[#156287]/15 ring-1 ring-[#156287]/30"
                  : "border-surface-700/80 bg-surface-900/40 dark:bg-surface-900/70 hover:border-[#156287]/50 dark:hover:border-sky-400/40",
              )}
            >
              {/* Título arriba */}
              <span className="font-bold text-xs sm:text-sm text-foreground line-clamp-2 min-h-[2.25rem] flex items-center justify-center leading-tight">
                {c.name}
              </span>

              {/* Centro: Imagen o Icono visual temático */}
              <VisualBadge candidate={c} />

              {/* Botón de acción */}
              <button
                type="button"
                onClick={() => handleToggleCandidate(c)}
                disabled={isPending}
                className={cn(
                  "text-[11px] sm:text-xs font-semibold rounded-full px-2.5 py-1.5 mt-2 w-full transition-all cursor-pointer flex items-center justify-center gap-1.5 active:scale-95 disabled:opacity-50",
                  isActive
                    ? "text-[#156287] dark:text-sky-200 bg-[#156287]/20 dark:bg-sky-500/20 border border-[#156287]/50 dark:border-sky-400/40 hover:bg-alert-red/10 hover:text-alert-red hover:border-alert-red/40 group"
                    : "text-[#156287] dark:text-sky-300 bg-[#156287]/10 hover:bg-[#156287]/20 dark:bg-sky-500/10 dark:hover:bg-sky-500/20 border border-[#156287]/30 dark:border-sky-400/30 shadow-2xs",
                )}
              >
                {isActive ? (
                  <>
                    <Check className="size-3 stroke-[2.5]" />
                    <span className="truncate group-hover:hidden">Alerta activa</span>
                    <span className="truncate hidden group-hover:inline">Desactivar</span>
                  </>
                ) : (
                  <>
                    <Bell className="size-3" />
                    <span className="truncate">Activar alerta</span>
                  </>
                )}
              </button>
            </div>
          );
        })}

        {/* Tarjeta final: Otra alerta / Personalizar */}
        <div className="w-[142px] sm:w-[160px] shrink-0 rounded-2xl border border-dashed border-surface-600/60 bg-surface-900/20 dark:bg-surface-900/40 p-3.5 sm:p-4 flex flex-col items-center justify-between text-center hover:border-[#156287]/60 transition-all">
          <span className="font-bold text-xs sm:text-sm text-foreground line-clamp-2 min-h-[2.25rem] flex items-center justify-center leading-tight">
            Otra alerta
          </span>

          <div className="size-16 sm:size-20 rounded-2xl border border-dashed border-surface-600/40 bg-surface-800/60 flex items-center justify-center my-2.5 text-muted-foreground">
            <Plus className="size-7 stroke-[1.8]" />
          </div>

          <button
            type="button"
            onClick={handleCustomize}
            className="text-[11px] sm:text-xs font-semibold text-muted-foreground hover:text-foreground bg-surface-700/40 hover:bg-surface-700/80 border border-surface-600/40 rounded-full px-2.5 py-1.5 mt-2 w-full transition-all cursor-pointer active:scale-95 flex items-center justify-center gap-1.5"
          >
            <SlidersHorizontal className="size-3" />
            <span>Personalizar</span>
          </button>
        </div>
      </div>
    </section>
  );
}
