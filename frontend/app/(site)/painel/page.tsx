"use client";

import { Ban, Banknote, Plus, Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Alert, Button, ButtonLink, Countdown, Input, LotImage, Pagination, RequireAuth, StatusBadge } from "@/components";
import { useCancelLotMutation, useDebouncedValue, useMyLotsQuery, useNow } from "@/hooks";
import type { MyLotsSort } from "@/hooks";
import { cn, formatMoney, lotPhase, toApiError } from "@/lib";
import type { LotPhase } from "@/lib";
import type { MyLot } from "@/types";

const SORTS: { value: string; label: string; sort?: MyLotsSort; dir?: "asc" | "desc" }[] = [
  { value: "recent", label: "Mais recentes", sort: "created_at", dir: "desc" },
  { value: "ending", label: "A terminar primeiro", sort: "ends_at", dir: "asc" },
  { value: "bid", label: "Maior lance", sort: "current_bid", dir: "desc" },
  { value: "title", label: "Título (A-Z)", sort: "title", dir: "asc" },
];

export default function AuctioneerPanelPage() {
  return <RequireAuth role="AUCTIONEER">{() => <PanelContent />}</RequireAuth>;
}

function PanelContent() {
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState("recent");
  const [page, setPage] = useState(1);
  const filter = useDebouncedValue(search.trim());
  const sort = SORTS.find((option) => option.value === sortKey) ?? SORTS[0];

  const { data, isPending, isError, error, isPlaceholderData } = useMyLotsQuery({
    filter,
    page,
    per_page: 10,
    sort: sort.sort,
    sort_dir: sort.dir,
  });

  return (
    <div className="container max-w-5xl space-y-8 py-10">
      <section className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="space-y-2">
          <h1 className="text-3xl font-extrabold text-white">Painel do leiloeiro</h1>
          <p className="text-neutral-400">Os seus lotes, os resultados de cada leilão e o total recebido.</p>
        </div>
        <ButtonLink href="/painel/novo" className="px-5 py-2.5">
          <Plus size={18} aria-hidden="true" />
          Novo lote
        </ButtonLink>
      </section>

      <div className="flex items-center gap-4 rounded-xl border border-neutral-900 bg-background-elevated p-5">
        <Banknote size={28} className="text-primary" aria-hidden="true" />
        <div>
          <p className="text-sm text-neutral-400">Total recebido (lotes vendidos)</p>
          {isPending ? (
            <div className="mt-1 h-8 w-32 animate-pulse rounded bg-neutral-900" />
          ) : (
            <p className="text-2xl font-extrabold tabular-nums text-primary">{formatMoney(data?.total_received ?? "0")}</p>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <Input
          type="search"
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
          }}
          placeholder="Pesquisar por obra ou artista"
          aria-label="Pesquisar por obra ou artista"
          maxLength={100}
          containerClassName="flex-1"
          icon={<Search size={16} className="text-neutral-500" aria-hidden="true" />}
        />
        <select
          value={sortKey}
          onChange={(event) => {
            setSortKey(event.target.value);
            setPage(1);
          }}
          aria-label="Ordenar"
          className="rounded border border-neutral-700 bg-background px-3 py-3 text-sm text-neutral-200 outline-none focus:border-primary/60"
        >
          {SORTS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {isError ? (
        <Alert>{toApiError(error).message}</Alert>
      ) : isPending ? (
        <p className="py-16 text-center text-neutral-400">A carregar…</p>
      ) : data.data.length === 0 ? (
        <div className="space-y-4 rounded-xl border border-dashed border-neutral-800 py-16 text-center">
          <p className="text-neutral-400">{filter ? `Nenhum lote corresponde a "${filter}".` : "Ainda não criou nenhum lote."}</p>
          {!filter && (
            <ButtonLink href="/painel/novo" variant="outline">
              Criar o primeiro lote
            </ButtonLink>
          )}
        </div>
      ) : (
        <div className={cn("space-y-6 transition-opacity", isPlaceholderData && "opacity-60")}>
          <ul className="space-y-3">
            {data.data.map((lot) => (
              <MyLotRow key={lot.id} lot={lot} />
            ))}
          </ul>
          <Pagination meta={data.meta} onPageChange={setPage} />
        </div>
      )}
    </div>
  );
}

function MyLotRow({ lot }: { lot: MyLot }) {
  const now = useNow();
  const phase = lotPhase(lot, now);
  const cancel = useCancelLotMutation();
  const [confirming, setConfirming] = useState(false);
  const cancellable = phase === "live" || phase === "scheduled";

  return (
    <li className="space-y-3 rounded-xl border border-neutral-900 bg-background-elevated p-3">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <Link href={`/lotes/${lot.id}`} className="shrink-0">
          <LotImage src={lot.image_url} alt={lot.title} sizes="160px" className="aspect-4/3 w-full rounded-lg sm:w-40" />
        </Link>

        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <Link href={`/lotes/${lot.id}`} className="truncate font-bold text-white hover:underline">
              {lot.title}
            </Link>
            <StatusBadge phase={phase} />
          </div>
          <p className="truncate text-sm text-neutral-400">
            {[lot.attributes.artist, lot.attributes.date].filter(Boolean).join(" · ") || "Autor desconhecido"}
          </p>
          <p className="text-xs text-neutral-500">
            Inicial {formatMoney(lot.starting_bid)} · incremento {formatMoney(lot.min_increment)} · {lot.bid_count}{" "}
            {lot.bid_count === 1 ? "lance" : "lances"}
          </p>
          <Countdown lot={lot} phase={phase} now={now} className="text-xs" />
        </div>

        <div className="text-sm sm:w-56">
          <Result lot={lot} phase={phase} />
        </div>

        <div className="flex shrink-0 gap-2 sm:flex-col">
          <ButtonLink href={`/lotes/${lot.id}`} variant="outline" className="px-4 py-2 text-sm">
            Ver lote
          </ButtonLink>
          {cancellable && !confirming && (
            <Button variant="ghost" onClick={() => setConfirming(true)} className="px-4 py-2 text-sm text-red-300">
              <Ban size={16} aria-hidden="true" />
              Cancelar
            </Button>
          )}
        </div>
      </div>

      {confirming && cancellable && (
        <div role="alertdialog" aria-label="Confirmar cancelamento" className="flex flex-col gap-3 rounded border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-100 sm:flex-row sm:items-center sm:justify-between">
          <p>
            Cancelar o leilão de <strong>{lot.title}</strong>?{" "}
            {lot.bid_count > 0
              ? `O licitante que lidera recebe de volta ${formatMoney(lot.current_bid)}.`
              : "Ainda não há lances."}{" "}
            Não é possível desfazer.
          </p>
          <div className="flex shrink-0 gap-2">
            <Button variant="ghost" onClick={() => setConfirming(false)} className="px-4 py-2 text-sm">
              Manter
            </Button>
            <Button
              onClick={() => cancel.mutate(lot.id, { onSettled: () => setConfirming(false) })}
              disabled={cancel.isPending}
              className="bg-red-500 px-4 py-2 text-sm text-[#fff] hover:bg-red-500/90 disabled:opacity-50"
            >
              {cancel.isPending ? "A cancelar…" : "Sim, cancelar"}
            </Button>
          </div>
        </div>
      )}
      {cancel.isError && <Alert>{cancel.error.message}</Alert>}
    </li>
  );
}

function Result({ lot, phase }: { lot: MyLot; phase: LotPhase }) {
  if (phase === "cancelled") return <p className="text-neutral-400">Cancelado; valores devolvidos.</p>;
  if (phase === "ended") {
    return lot.result.sold ? (
      <div>
        <p className="text-xs text-neutral-500">Vendido a {lot.result.winner_alias}</p>
        <p className="text-lg font-extrabold tabular-nums text-primary">{formatMoney(lot.result.final_amount)}</p>
      </div>
    ) : (
      <p className="text-neutral-400">Encerrado sem lances.</p>
    );
  }
  return (
    <div>
      <p className="text-xs text-neutral-500">{lot.current_bid ? "Lance atual" : "Sem lances ainda"}</p>
      <p className="text-lg font-extrabold tabular-nums text-white">{formatMoney(lot.current_bid ?? lot.starting_bid)}</p>
    </div>
  );
}
