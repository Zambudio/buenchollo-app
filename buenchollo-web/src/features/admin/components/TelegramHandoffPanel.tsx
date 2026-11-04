/** Panel de Telegram (carga diferida) controlado por useTelegramHandoff. */
import { lazy, Suspense } from "react";
import type { TelegramScheduleRequest } from "@/features/telegram/components/TelegramPanel";
import type { TelegramHandoff } from "../hooks/useTelegramHandoff";

const TelegramPanel = lazy(() =>
  import("@/features/telegram/components/TelegramPanel").then((m) => ({
    default: m.TelegramPanel,
  })),
);

interface Props {
  readonly handoff: TelegramHandoff;
  readonly onSchedule?: (request: TelegramScheduleRequest) => Promise<boolean>;
}

export function TelegramHandoffPanel({ handoff, onSchedule }: Props) {
  if (!handoff.open || !handoff.data) return null;
  return (
    <Suspense
      fallback={
        <div className="fixed inset-0 z-50 bg-background/80 flex items-center justify-center font-mono text-xs text-cyan-glow">
          Cargando panel Telegram...
        </div>
      }
    >
      <TelegramPanel
        dealData={handoff.data}
        onClose={handoff.close}
        onSchedule={handoff.canSchedule ? onSchedule : undefined}
        defaultScheduledAt={handoff.defaultScheduledAt}
      />
    </Suspense>
  );
}
