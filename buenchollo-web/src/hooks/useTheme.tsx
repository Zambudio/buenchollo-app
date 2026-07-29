import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type Theme = "dark" | "light";
export type ThemeMode = Theme | "system";

export const THEME_STORAGE_KEY = "buenchollo-theme";

/** Script bloqueante ejecutado en <head>, antes de pintar, para evitar FOUC. */
export const THEME_INIT_SCRIPT = `(function(){try{var s=localStorage.getItem('${THEME_STORAGE_KEY}');var m=(s==='light'||s==='dark'||s==='system')?s:'system';var t=m==='system'?((window.matchMedia&&window.matchMedia('(prefers-color-scheme: light)').matches)?'light':'dark'):m;document.documentElement.classList.toggle('dark',t==='dark');}catch(e){}})();`;

function systemPrefersLight(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function"
    ? window.matchMedia("(prefers-color-scheme: light)").matches
    : false;
}

function resolveTheme(mode: ThemeMode): Theme {
  if (mode === "system") return systemPrefersLight() ? "light" : "dark";
  return mode;
}

function resolveInitialMode(): ThemeMode {
  if (typeof window === "undefined") return "system";
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "light" || stored === "dark" || stored === "system") return stored;
  } catch {
    /* localStorage no disponible (modo privado, SSR, etc.) */
  }
  return "system";
}

interface ThemeContextValue {
  /** Tema efectivo aplicado (resuelto desde `mode` cuando es "system"). */
  theme: Theme;
  /** Preferencia elegida por el usuario: claro/oscuro explícito o "system" (seguir al SO). */
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
  /** Atajo binario: alterna entre claro/oscuro explícito (no afecta a "system"). */
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(() => resolveInitialMode());
  const [theme, setTheme] = useState<Theme>(() => resolveTheme(mode));

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute("content", theme === "dark" ? "#0b1120" : "#f8fafc");
  }, [theme]);

  // En modo "system", sigue los cambios de preferencia del SO en vivo mientras
  // la pestaña está abierta (p. ej. el usuario cambia el tema de Windows).
  useEffect(() => {
    if (mode !== "system" || typeof window.matchMedia !== "function") return;
    const mql = window.matchMedia("(prefers-color-scheme: light)");
    const onChange = () => setTheme(mql.matches ? "light" : "dark");
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [mode]);

  const setMode = (next: ThemeMode) => {
    setModeState(next);
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      /* no crítico */
    }
    setTheme(resolveTheme(next));
  };

  const toggleTheme = () => {
    setMode(theme === "dark" ? "light" : "dark");
  };

  return (
    <ThemeContext.Provider value={{ theme, mode, setMode, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme debe usarse dentro de ThemeProvider");
  return ctx;
}
