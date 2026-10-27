import { cn } from "@/lib";
import type { BidSituation } from "@/types";

const LABEL: Record<BidSituation, string> = {
  winning: "Está a ganhar",
  outbid: "Superado",
  won: "Arrematado",
  lost: "Não arrematado",
  cancelled: "Cancelado",
};

const STYLE: Record<BidSituation, string> = {
  winning: "bg-emerald-500/15 text-emerald-200 border-emerald-500/40",
  outbid: "bg-amber-500/15 text-amber-200 border-amber-500/40",
  won: "bg-primary/15 text-primary border-primary/40",
  lost: "bg-neutral-800 text-neutral-400 border-neutral-700",
  cancelled: "bg-neutral-800 text-neutral-400 border-neutral-700",
};

export function SituationBadge({ situation, className }: { situation: BidSituation; className?: string }) {
  return (
    <span className={cn("inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold", STYLE[situation], className)}>
      {LABEL[situation]}
    </span>
  );
}
