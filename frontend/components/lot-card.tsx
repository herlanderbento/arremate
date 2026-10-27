"use client";

import Link from "next/link";
import { useNow } from "@/hooks";
import { formatMoney, lotPhase } from "@/lib";
import type { Lot } from "@/types";
import { Countdown } from "./countdown";
import { LotImage } from "./lot-image";
import { StatusBadge } from "./status-badge";

export function LotCard({ lot, priority }: { lot: Lot; priority?: boolean }) {
  const now = useNow();
  const phase = lotPhase(lot, now);
  const artist = lot.attributes.artist;

  return (
    <Link
      href={`/lotes/${lot.id}`}
      className="group flex flex-col overflow-hidden rounded-xl border border-neutral-900 bg-background-elevated transition-colors hover:border-neutral-700 focus-visible:outline-2 focus-visible:outline-primary"
    >
      <div className="relative">
        <LotImage
          src={lot.image_url}
          alt={lot.title}
          sizes="(min-width: 1024px) 25vw, (min-width: 640px) 50vw, 100vw"
          priority={priority}
          className="aspect-4/3 transition-transform group-hover:scale-[1.02]"
        />
        <StatusBadge phase={phase} className="absolute left-3 top-3 backdrop-blur" />
      </div>

      <div className="flex flex-1 flex-col gap-3 p-4">
        <div>
          <h3 className="line-clamp-1 font-bold text-white">{lot.title}</h3>
          <p className="line-clamp-1 text-sm text-neutral-400">
            {[artist, lot.attributes.date].filter(Boolean).join(" · ") || "Autor desconhecido"}
          </p>
        </div>

        <div className="mt-auto flex items-end justify-between gap-3">
          <div>
            <p className="text-xs text-neutral-500">
              {lot.current_bid ? `Lance atual · ${lot.bid_count} ${lot.bid_count === 1 ? "lance" : "lances"}` : "Lance inicial"}
            </p>
            <p className="text-lg font-extrabold text-primary tabular-nums">
              {formatMoney(lot.current_bid ?? lot.starting_bid)}
            </p>
          </div>
          <Countdown lot={lot} phase={phase} now={now} className="text-right text-xs" />
        </div>
      </div>
    </Link>
  );
}
