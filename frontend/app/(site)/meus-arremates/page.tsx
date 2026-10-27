"use client";

import { FileCheck2, Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Alert, ButtonLink, CopyLinkButton, Countdown, Input, LotImage, Pagination, RequireAuth, SituationBadge } from "@/components";
import { useDebouncedValue, useMyBidsQuery, useNow } from "@/hooks";
import { cn, formatMoney, lotPhase, toApiError } from "@/lib";
import type { MyBid } from "@/types";

export default function MyBidsPage() {
  return <RequireAuth role="BIDDER">{() => <MyBidsContent />}</RequireAuth>;
}

function MyBidsContent() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const filter = useDebouncedValue(search.trim());
  const { data, isPending, isError, error, isPlaceholderData } = useMyBidsQuery({ filter, page, per_page: 10 });

  return (
    <div className="container max-w-5xl space-y-8 py-10">
      <section className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="space-y-2">
          <h1 className="text-3xl font-extrabold text-white">Meus arremates</h1>
          <p className="text-neutral-400">Os lotes em que licitou: onde está a ganhar, onde foi superado e as obras que arrematou.</p>
        </div>
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
          containerClassName="md:w-72"
          icon={<Search size={16} className="text-neutral-500" aria-hidden="true" />}
        />
      </section>

      {isError ? (
        <Alert>{toApiError(error).message}</Alert>
      ) : isPending ? (
        <p className="py-16 text-center text-neutral-400">A carregar…</p>
      ) : data.data.length === 0 ? (
        <div className="space-y-4 rounded-xl border border-dashed border-neutral-800 py-16 text-center">
          <p className="text-neutral-400">
            {filter ? `Nenhum lote corresponde a "${filter}".` : "Ainda não deu nenhum lance."}
          </p>
          {!filter && (
            <ButtonLink href="/" variant="outline">
              Ver leilões ao vivo
            </ButtonLink>
          )}
        </div>
      ) : (
        <div className={cn("space-y-6 transition-opacity", isPlaceholderData && "opacity-60")}>
          <ul className="space-y-3">
            {data.data.map((bid) => (
              <MyBidRow key={bid.id} bid={bid} />
            ))}
          </ul>
          <Pagination meta={data.meta} onPageChange={setPage} />
        </div>
      )}
    </div>
  );
}

function MyBidRow({ bid }: { bid: MyBid }) {
  const now = useNow();
  const phase = lotPhase(bid, now);
  const won = bid.situation === "won";

  return (
    <li
      className={cn(
        "flex flex-col gap-4 rounded-xl border bg-background-elevated p-3 sm:flex-row sm:items-center",
        won ? "border-primary/40" : "border-neutral-900"
      )}
    >
      <Link href={`/lotes/${bid.id}`} className="shrink-0">
        <LotImage src={bid.image_url} alt={bid.title} sizes="160px" className="aspect-4/3 w-full rounded-lg sm:w-40" />
      </Link>

      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <Link href={`/lotes/${bid.id}`} className="truncate font-bold text-white hover:underline">
            {bid.title}
          </Link>
          <SituationBadge situation={bid.situation} />
        </div>
        <p className="truncate text-sm text-neutral-400">
          {[bid.attributes.artist, bid.attributes.date].filter(Boolean).join(" · ") || "Autor desconhecido"}
        </p>
        <p className="text-xs text-neutral-500">O seu pseudónimo neste lote: {bid.my_alias}</p>
        <Countdown lot={bid} phase={phase} now={now} className="text-xs" />
      </div>

      <dl className="grid grid-cols-2 gap-4 text-sm sm:w-64">
        <div>
          <dt className="text-xs text-neutral-500">O seu maior lance</dt>
          <dd className="font-semibold tabular-nums text-white">{formatMoney(bid.my_max_bid)}</dd>
        </div>
        <div>
          <dt className="text-xs text-neutral-500">{won ? "Valor pago" : "Lance atual"}</dt>
          <dd className={cn("font-semibold tabular-nums", won ? "text-primary" : "text-white")}>
            {formatMoney(bid.current_bid)}
          </dd>
        </div>
      </dl>

      <div className="flex shrink-0 gap-2 sm:flex-col">
        {won && bid.receipt_token ? (
          <>
            <ButtonLink href={`/comprovativos/${bid.receipt_token}`} className="px-4 py-2 text-sm">
              <FileCheck2 size={16} aria-hidden="true" />
              Comprovativo
            </ButtonLink>
            <CopyLinkButton path={`/comprovativos/${bid.receipt_token}`} className="px-4 py-2 text-sm" />
          </>
        ) : bid.situation === "outbid" && phase === "live" ? (
          <ButtonLink href={`/lotes/${bid.id}`} className="px-4 py-2 text-sm">
            Licitar de novo
          </ButtonLink>
        ) : (
          <ButtonLink href={`/lotes/${bid.id}`} variant="outline" className="px-4 py-2 text-sm">
            Ver lote
          </ButtonLink>
        )}
      </div>
    </li>
  );
}
