import type { LotPhase } from "@/lib";
import { cn } from "@/lib";

const LABEL: Record<LotPhase, string> = {
  live: "Ao vivo",
  closing: "A encerrar",
  scheduled: "Agendado",
  ended: "Encerrado",
  cancelled: "Cancelado",
};

const STYLE: Record<LotPhase, string> = {
  live: "bg-red-500/15 text-red-300 border-red-500/40",
  closing: "bg-amber-500/15 text-amber-200 border-amber-500/40",
  scheduled: "bg-sky-500/15 text-sky-200 border-sky-500/40",
  ended: "bg-neutral-800 text-neutral-300 border-neutral-700",
  cancelled: "bg-neutral-800 text-neutral-400 border-neutral-700 line-through",
};

export function StatusBadge({ phase, className }: { phase: LotPhase; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        STYLE[phase],
        className
      )}
    >
      {phase === "live" && (
        <span className="size-1.5 rounded-full bg-red-400 animate-pulse" aria-hidden="true" />
      )}
      {LABEL[phase]}
    </span>
  );
}
