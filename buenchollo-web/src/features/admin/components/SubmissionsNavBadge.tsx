/** Contador de propuestas pendientes para el sidebar del admin. */
import { useAdminSubmissionsCount } from "../hooks/useAdminSubmissions";

export function SubmissionsNavBadge({ enabled }: { readonly enabled: boolean }) {
  const { data } = useAdminSubmissionsCount(enabled);
  const pending = data?.pending ?? 0;
  if (!enabled || pending <= 0) return null;
  const label = `${pending} ${pending === 1 ? "propuesta pendiente" : "propuestas pendientes"}`;
  return (
    <span
      role="status"
      aria-label={label}
      title={label}
      className="ml-auto min-w-5 h-5 px-1.5 inline-flex items-center justify-center bg-cyan-glow text-surface-900 font-mono text-[10px] font-bold"
    >
      {pending > 99 ? "99+" : pending}
    </span>
  );
}
