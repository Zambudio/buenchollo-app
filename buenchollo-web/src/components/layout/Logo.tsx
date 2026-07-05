import logoBcTech from "@/assets/logo-bctech.png";

export function Logo({ className = "" }: { className?: string }) {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <img
        src={logoBcTech}
        alt="BuenChollo Tech logo"
        className="size-9 sm:size-10 object-contain drop-shadow-[0_0_8px_rgba(34,211,238,0.55)]"
        loading="eager"
        decoding="async"
      />
      <div className="font-bold text-lg sm:text-xl tracking-tighter text-foreground">
        BuenChollo<span className="text-cyan-glow"> Tech</span>
      </div>
    </div>
  );
}
