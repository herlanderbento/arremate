"use client";

import { ArrowLeft, CircleCheck, Clock, ShieldCheck, TrendingDown, Trophy, Wifi, WifiOff } from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";
import { Alert, ButtonLink, Countdown, LotImage, StatusBadge } from "@/components";
import { useLotQuery, useLotRoom, useMeQuery, useNow } from "@/hooks";
import type { LotDetailView, RoomConnection } from "@/hooks";
import { cn, formatMoney, formatTime, lotPhase, toApiError } from "@/lib";
import type { LotPhase } from "@/lib";
import type { LotRoomEvent } from "@/types";
import { BidForm } from "./bid-form";

export function LotRoom({ id }: { id: string }) {
  const { data: lot, isPending, isError, error, refetch } = useLotQuery(id);
  const finished = lot?.status === "ended" || lot?.status === "cancelled";
  const { connection, lastEvent } = useLotRoom(id, !!lot && !finished);
  const now = useNow(lot?.clock_offset_ms ?? 0);
  const phase = lot ? lotPhase(lot, now) : null;

  useEffect(() => {
    if (phase === "closing") {
      const retry = setInterval(() => refetch(), 3000);
      void refetch();
      return () => clearInterval(retry);
    }
    if (phase === "live" && lot?.status === "scheduled") void refetch();
  }, [phase, lot?.status, refetch]);

  if (isPending) {
    return <p className="container py-20 text-center text-neutral-400">A carregar o lote…</p>;
  }
  if (isError || !lot || !phase) {
    const apiError = toApiError(error);
    const notFound = apiError.status === 404 || apiError.status === 422;
    return (
      <div className="container max-w-lg space-y-4 py-20 text-center">
        <Alert>{notFound ? "Lote não encontrado." : apiError.message}</Alert>
        <ButtonLink href="/" variant="outline">
          Voltar à vitrine
        </ButtonLink>
      </div>
    );
  }

  const { artist, date, medium } = lot.attributes;

  return (
    <div className="container space-y-6 py-8">
      <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-neutral-400 hover:text-white">
        <ArrowLeft size={16} aria-hidden="true" />
        Vitrine
      </Link>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_420px]">
        <section className="space-y-4">
          <LotImage
            src={lot.image_url}
            alt={lot.title}
            sizes="(min-width: 1024px) 60vw, 100vw"
            priority
            className="aspect-4/3 rounded-xl border border-neutral-900"
          />
          <dl className="grid grid-cols-2 gap-4 rounded-xl border border-neutral-900 bg-background-elevated p-4 text-sm sm:grid-cols-3">
            <Detail label="Artista" value={artist} />
            <Detail label="Data" value={date} />
            <Detail label="Técnica" value={medium} />
            <Detail label="Lance inicial" value={formatMoney(lot.starting_bid)} />
            <Detail label="Incremento mínimo" value={formatMoney(lot.min_increment)} />
            <Detail label="Lances" value={String(lot.bid_count)} />
          </dl>
        </section>

        <aside className="space-y-4 lg:sticky lg:top-24 lg:self-start">
          <div className="space-y-4 rounded-xl border border-neutral-900 bg-background-elevated p-5">
            <div className="flex items-center justify-between gap-3">
              <StatusBadge phase={phase} />
              {!finished && <ConnectionIndicator connection={connection} />}
            </div>

            <div>
              <h1 className="text-2xl font-extrabold text-white">{lot.title}</h1>
              {artist && <p className="text-neutral-400">{artist}</p>}
            </div>

            <div className="grid grid-cols-2 gap-4 border-y border-neutral-900 py-4">
              <div>
                <p className="text-xs text-neutral-500">{lot.current_bid ? "Lance atual" : "Lance inicial"}</p>
                <p className="text-2xl font-extrabold text-primary tabular-nums" aria-live="polite">
                  {formatMoney(lot.current_bid ?? lot.starting_bid)}
                </p>
                {lot.leader_alias && (
                  <p className="text-xs text-neutral-500">
                    {phase === "ended" ? "Vencedor" : "Lidera"}: {lot.leader_alias}
                  </p>
                )}
              </div>
              <div className="text-right">
                <Countdown lot={lot} phase={phase} now={now} className="flex flex-col text-sm [&_time]:text-xl" />
              </div>
            </div>

            <ExtendedNotice lastEvent={lastEvent} />
            <StandingBanner lot={lot} phase={phase} />
            <BidForm lot={lot} phase={phase} />
          </div>

          <BidHistory lot={lot} />
        </aside>
      </div>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string | undefined }) {
  return (
    <div>
      <dt className="text-neutral-500">{label}</dt>
      <dd className="font-medium text-neutral-200">{value || "—"}</dd>
    </div>
  );
}

function ConnectionIndicator({ connection }: { connection: RoomConnection }) {
  const open = connection === "open";
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs", open ? "text-emerald-300" : "text-neutral-500")}>
      {open ? <Wifi size={14} aria-hidden="true" /> : <WifiOff size={14} aria-hidden="true" />}
      {open ? "Em tempo real" : connection === "connecting" ? "A ligar…" : "Sem ligação, a tentar de novo…"}
    </span>
  );
}

function ExtendedNotice({ lastEvent }: { lastEvent: LotRoomEvent | null }) {
  if (lastEvent?.type !== "lot_extended") return null;
  return (
    <p role="status" className="flex items-start gap-2 rounded border border-sky-500/40 bg-sky-500/10 px-3 py-2.5 text-sm text-sky-200">
      <Clock size={18} className="mt-0.5 shrink-0" aria-hidden="true" />
      Lance nos últimos minutos: o leilão foi prolongado até {formatTime(lastEvent.ends_at)}.
    </p>
  );
}

function StandingBanner({ lot, phase }: { lot: LotDetailView; phase: LotPhase }) {
  const { data: user } = useMeQuery();
  const me = lot.my_alias;
  if (user?.role !== "BIDDER" || !me || !lot.bids.some((bid) => bid.bidder_alias === me)) return null;

  const leading = lot.leader_alias === me;

  if (phase === "cancelled") return null;
  if (phase === "ended") {
    return leading ? (
      <div role="status" className="space-y-2 rounded border border-emerald-500/40 bg-emerald-500/10 px-3 py-2.5 text-sm text-emerald-200">
        <p className="flex items-center gap-2 font-semibold">
          <Trophy size={18} aria-hidden="true" />
          Arrematou esta obra por {formatMoney(lot.current_bid)}.
        </p>
        <Link href="/meus-arremates" className="underline underline-offset-2 hover:text-white">
          Ver o comprovativo em Meus arremates
        </Link>
      </div>
    ) : (
      <p role="status" className="rounded border border-neutral-700 bg-neutral-800/50 px-3 py-2.5 text-sm text-neutral-300">
        Leilão encerrado. Desta vez outro licitante ficou com a obra; o seu saldo foi libertado.
      </p>
    );
  }

  return leading ? (
    <p role="status" className="flex items-center gap-2 rounded border border-emerald-500/40 bg-emerald-500/10 px-3 py-2.5 text-sm font-semibold text-emerald-200">
      <CircleCheck size={18} aria-hidden="true" />
      Você está ganhando.
    </p>
  ) : (
    <p role="alert" className="flex items-center gap-2 rounded border border-amber-500/40 bg-amber-500/10 px-3 py-2.5 text-sm font-semibold text-amber-200">
      <TrendingDown size={18} aria-hidden="true" />
      Você foi superado. Dê um novo lance para voltar à liderança.
    </p>
  );
}

function BidHistory({ lot }: { lot: LotDetailView }) {
  return (
    <section className="rounded-xl border border-neutral-900 bg-background-elevated p-5">
      <h2 className="mb-3 font-bold text-white">Histórico de lances</h2>
      {lot.bids.length === 0 ? (
        <p className="text-sm text-neutral-500">Ainda sem lances. O primeiro tem de ser de pelo menos {formatMoney(lot.starting_bid)}.</p>
      ) : (
        <ol className="max-h-96 space-y-1 overflow-y-auto text-sm">
          {lot.bids.map((bid, index) => {
            const mine = bid.bidder_alias === lot.my_alias;
            return (
              <li
                key={bid.seq}
                className={cn(
                  "flex items-center justify-between gap-3 rounded px-2 py-1.5",
                  index === 0 && "bg-primary/10",
                  mine && "font-semibold"
                )}
              >
                <span className="text-neutral-500 tabular-nums">#{bid.seq}</span>
                <span className="flex-1 truncate text-neutral-300">
                  {bid.bidder_alias}
                  {mine && <span className="ml-1 text-primary">(você)</span>}
                </span>
                <span className="tabular-nums text-white">{formatMoney(bid.amount)}</span>
                <time dateTime={bid.created_at} className="w-16 text-right text-xs text-neutral-500 tabular-nums">
                  {formatTime(bid.created_at)}
                </time>
              </li>
            );
          })}
        </ol>
      )}
      <p className="mt-3 text-xs text-neutral-500">
        Os licitantes aparecem só por um pseudónimo deste lote. Cada lance fica encadeado por hash, o que torna qualquer alteração detetável.
      </p>
      <Link
        href={`/auditoria/${lot.id}`}
        className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-primary hover:underline"
      >
        <ShieldCheck size={16} aria-hidden="true" />
        Verificar a integridade do histórico
      </Link>
    </section>
  );
}
