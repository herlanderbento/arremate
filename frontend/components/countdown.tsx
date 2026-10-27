import { formatDateTime, formatDuration } from "@/lib";
import type { LotPhase } from "@/lib";
import type { Lot } from "@/types";

type CountdownProps = {
  lot: Pick<Lot, "starts_at" | "ends_at">;
  phase: LotPhase;
  now: number | null;
  className?: string;
};

export function Countdown({ lot, phase, now, className = "" }: CountdownProps) {
  let label: string;
  let value: string;

  if (phase === "scheduled") {
    label = "Começa em";
    value = now === null ? formatDateTime(lot.starts_at) : formatDuration(Date.parse(lot.starts_at) - now);
  } else if (phase === "live") {
    label = "Termina em";
    value = now === null ? formatDateTime(lot.ends_at) : formatDuration(Date.parse(lot.ends_at) - now);
  } else if (phase === "closing") {
    label = "Tempo esgotado";
    value = "a apurar o vencedor…";
  } else {
    label = phase === "cancelled" ? "Cancelado" : "Encerrado em";
    value = phase === "cancelled" ? "" : formatDateTime(lot.ends_at);
  }

  return (
    <p className={className}>
      <span className="text-neutral-400">{label}</span>{" "}
      <time dateTime={phase === "scheduled" ? lot.starts_at : lot.ends_at} className="font-semibold tabular-nums">
        {value}
      </time>
    </p>
  );
}
