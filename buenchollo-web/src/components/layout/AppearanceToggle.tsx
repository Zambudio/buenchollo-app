import { Moon, Sun } from "lucide-react";
import { useTheme, type ThemeMode } from "@/hooks/useTheme";

const OPTIONS: { value: ThemeMode; icon?: typeof Sun; label?: string; ariaLabel: string }[] = [
  { value: "light", icon: Sun, ariaLabel: "Tema claro" },
  { value: "dark", icon: Moon, ariaLabel: "Tema oscuro" },
  { value: "system", label: "Auto", ariaLabel: "Seguir el tema del sistema" },
];

/** Selector de apariencia de 3 vías (claro / oscuro / auto = sigue al SO). */
export function AppearanceToggle() {
  const { mode, setMode } = useTheme();

  return (
    <div className="inline-flex items-center gap-1 rounded-full border border-surface-600 bg-surface-900 p-1">
      {OPTIONS.map(({ value, icon: Icon, label, ariaLabel }) => {
        const active = mode === value;
        return (
          <button
            key={value}
            type="button"
            onClick={() => setMode(value)}
            aria-pressed={active}
            aria-label={ariaLabel}
            className={`flex items-center justify-center rounded-full transition-colors ${
              label ? "px-3 py-1.5 text-xs font-mono font-bold" : "size-8"
            } ${
              active
                ? "bg-cyan-glow/15 text-cyan-glow ring-1 ring-inset ring-cyan-glow/50"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {Icon ? <Icon className="size-4" /> : label}
          </button>
        );
      })}
    </div>
  );
}
