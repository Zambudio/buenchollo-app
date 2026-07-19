import { Percent, Sparkles, TrendingUp } from "lucide-react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

export type HomeFilterKey = "popular" | "recent" | "discount";

const OPTIONS: { value: HomeFilterKey; label: string; icon: typeof TrendingUp }[] = [
  { value: "popular", label: "Más populares", icon: TrendingUp },
  { value: "recent", label: "Nuevos", icon: Sparkles },
  { value: "discount", label: "Mayor descuento", icon: Percent },
];

interface Props {
  readonly value: HomeFilterKey;
  readonly onChange: (value: HomeFilterKey) => void;
}

export function HomeFilterTabs({ value, onChange }: Props) {
  return (
    <Tabs value={value} onValueChange={(v) => onChange(v as HomeFilterKey)}>
      <TabsList className="inline-flex h-auto w-fit max-w-full items-center gap-1 bg-surface-800 border border-surface-700 rounded-full p-1">
        {OPTIONS.map(({ value: v, label, icon: Icon }) => (
          <TabsTrigger
            key={v}
            value={v}
            className="min-w-0 flex-1 sm:flex-none font-mono text-[10px] max-[359px]:text-[9px] sm:text-xs uppercase tracking-normal sm:tracking-wide rounded-full px-2 sm:px-4 py-2 gap-1 sm:gap-1.5 text-muted-foreground data-[state=active]:bg-cyan-glow data-[state=active]:text-surface-900 data-[state=active]:font-bold data-[state=active]:shadow-none"
          >
            <Icon className="size-3 sm:size-3.5 shrink-0 max-[359px]:hidden" />
            {label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}
