"use client";

import { Search } from "lucide-react";
import { useState } from "react";
import { Alert, Input, LotCard, Pagination } from "@/components";
import { useDebouncedValue, useLotsQuery } from "@/hooks";
import type { LotsStatusFilter } from "@/hooks";
import { cn, toApiError } from "@/lib";

const TABS: { value: LotsStatusFilter | undefined; label: string }[] = [
  { value: "live", label: "Ao vivo" },
  { value: "scheduled", label: "Agendados" },
  { value: "ended", label: "Encerrados" },
  { value: undefined, label: "Todos" },
];

const EMPTY: Record<string, string> = {
  live: "Nenhum leilão ao vivo neste momento.",
  scheduled: "Nenhum leilão agendado.",
  ended: "Ainda não há leilões encerrados.",
  all: "Nenhum lote encontrado.",
};

export default function ShowcasePage() {
  const [status, setStatus] = useState<LotsStatusFilter | undefined>("live");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const filter = useDebouncedValue(search.trim());

  const { data, isPending, isError, error, isPlaceholderData } = useLotsQuery({
    status,
    filter,
    page,
    per_page: 12,
  });

  const selectTab = (value: LotsStatusFilter | undefined) => {
    setStatus(value);
    setPage(1);
  };

  return (
    <div className="container space-y-8 py-10">
      <section className="space-y-3">
        <h1 className="text-3xl font-extrabold text-white md:text-4xl">Vitrine</h1>
        <p className="max-w-2xl text-neutral-400">
          Obras do Art Institute of Chicago em leilão. Entre num lote para acompanhar os lances em tempo real.
        </p>
      </section>

      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div role="tablist" aria-label="Estado do leilão" className="flex gap-1 overflow-x-auto rounded-lg bg-background-elevated p-1">
          {TABS.map((tab) => (
            <button
              key={tab.label}
              type="button"
              role="tab"
              aria-selected={status === tab.value}
              onClick={() => selectTab(tab.value)}
              className={cn(
                "whitespace-nowrap rounded-md px-4 py-2 text-sm font-semibold transition-colors",
                status === tab.value ? "bg-primary text-background" : "text-neutral-400 hover:text-white"
              )}
            >
              {tab.label}
            </button>
          ))}
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
          containerClassName="md:w-80"
          icon={<Search size={16} className="text-neutral-500" aria-hidden="true" />}
        />
      </div>

      {isError ? (
        <Alert>{toApiError(error).message}</Alert>
      ) : isPending ? (
        <LotGridSkeleton />
      ) : data.data.length === 0 ? (
        <p className="rounded-xl border border-dashed border-neutral-800 py-16 text-center text-neutral-400">
          {filter ? `Nenhum lote corresponde a "${filter}".` : EMPTY[status ?? "all"]}
        </p>
      ) : (
        <div className={cn("space-y-8 transition-opacity", isPlaceholderData && "opacity-60")}>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {data.data.map((lot, index) => (
              <LotCard key={lot.id} lot={lot} priority={index < 4} />
            ))}
          </div>
          <Pagination meta={data.meta} onPageChange={setPage} />
        </div>
      )}
    </div>
  );
}

function LotGridSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" aria-busy="true" aria-label="A carregar lotes">
      {Array.from({ length: 4 }, (_, index) => (
        <div key={index} className="overflow-hidden rounded-xl border border-neutral-900 bg-background-elevated">
          <div className="aspect-4/3 animate-pulse bg-neutral-900" />
          <div className="space-y-2 p-4">
            <div className="h-4 w-2/3 animate-pulse rounded bg-neutral-900" />
            <div className="h-3 w-1/2 animate-pulse rounded bg-neutral-900" />
          </div>
        </div>
      ))}
    </div>
  );
}
