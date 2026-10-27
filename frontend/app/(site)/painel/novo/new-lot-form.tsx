"use client";

import { ArrowLeft, Check, Search } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { FormEvent } from "react";
import { Alert, Button, FormField, Input, LotImage, Pagination } from "@/components";
import { useCatalogSearchQuery, useCreateLotMutation, useDebouncedValue, useNow } from "@/hooks";
import { cn, fieldErrors, formatDateTime, formatMoney, parseMoneyInput, toApiError } from "@/lib";
import type { CatalogItem } from "@/types";

const MINUTE = 60_000;

const DURATIONS = [
  { label: "10 min", ms: 10 * MINUTE },
  { label: "15 min", ms: 15 * MINUTE },
  { label: "1 hora", ms: 60 * MINUTE },
  { label: "1 dia", ms: 24 * 60 * MINUTE },
  { label: "7 dias", ms: 7 * 24 * 60 * MINUTE },
];

function toLocalInput(date: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function toIso(local: string): string | null {
  const time = Date.parse(local);
  return Number.isNaN(time) ? null : new Date(time).toISOString();
}

function nextMinute() {
  const date = new Date(Date.now() + MINUTE);
  date.setSeconds(0, 0);
  return date;
}

export function NewLotForm() {
  const router = useRouter();
  const createLot = useCreateLotMutation();
  const [item, setItem] = useState<CatalogItem | null>(null);
  const [startingBid, setStartingBid] = useState("");
  const [increment, setIncrement] = useState("");
  const [startsAt, setStartsAt] = useState(() => toLocalInput(nextMinute()));
  const [endsAt, setEndsAt] = useState(() => toLocalInput(new Date(nextMinute().getTime() + 60 * MINUTE)));
  const [touched, setTouched] = useState(false);
  const now = useNow();

  const starting = parseMoneyInput(startingBid);
  const step = parseMoneyInput(increment);
  const startsIso = toIso(startsAt);
  const endsIso = toIso(endsAt);
  const apiFields = fieldErrors(createLot.error);

  const errors = {
    starting_bid: !starting ? "Indique um valor positivo, com até 2 casas decimais." : apiFields.starting_bid,
    min_increment: !step ? "Indique um valor positivo, com até 2 casas decimais." : apiFields.min_increment,
    starts_at: !startsIso ? "Indique a data de início." : apiFields.starts_at,
    ends_at: !endsIso
      ? "Indique a data de fim."
      : startsIso && endsIso <= startsIso
        ? "O fim tem de ser depois do início."
        : now !== null && Date.parse(endsIso) <= now
          ? "O fim tem de estar no futuro."
          : apiFields.ends_at,
  };
  const valid = !!item && !!starting && !!step && !!startsIso && !!endsIso && endsIso > startsIso;

  const setDuration = (ms: number) => {
    const start = startsIso ? new Date(startsIso) : nextMinute();
    setEndsAt(toLocalInput(new Date(start.getTime() + ms)));
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setTouched(true);
    if (!valid || createLot.isPending) return;
    createLot.mutate(
      { external_id: item.external_id, starting_bid: starting, min_increment: step, starts_at: startsIso, ends_at: endsIso },
      { onSuccess: (lot) => router.push(`/lotes/${lot.id}`) }
    );
  };

  return (
    <div className="container max-w-5xl space-y-8 py-10">
      <div className="space-y-2">
        <Link href="/painel" className="inline-flex items-center gap-1.5 text-sm text-neutral-400 hover:text-white">
          <ArrowLeft size={16} aria-hidden="true" />
          Painel
        </Link>
        <h1 className="text-3xl font-extrabold text-white">Novo lote</h1>
        <p className="text-neutral-400">Escolha uma obra do catálogo do Art Institute of Chicago e defina as regras do leilão.</p>
      </div>

      <section className="space-y-4">
        <h2 className="text-lg font-bold text-white">1. Obra</h2>
        {item ? (
          <div className="flex items-center gap-4 rounded-xl border border-primary/40 bg-background-elevated p-3">
            <LotImage src={item.image_url} alt={item.title} sizes="128px" className="aspect-4/3 w-32 shrink-0 rounded-lg" />
            <div className="min-w-0 flex-1">
              <p className="truncate font-bold text-white">{item.title}</p>
              <p className="truncate text-sm text-neutral-400">
                {[item.attributes.artist, item.attributes.date].filter(Boolean).join(" · ") || "Autor desconhecido"}
              </p>
            </div>
            <Button variant="ghost" onClick={() => setItem(null)} className="px-4 py-2 text-sm">
              Trocar
            </Button>
          </div>
        ) : (
          <CatalogPicker onPick={setItem} />
        )}
        {touched && !item && <p className="text-sm text-red-300">Escolha uma obra.</p>}
      </section>

      <form onSubmit={submit} className="space-y-6" noValidate>
        <section className="space-y-4">
          <h2 className="text-lg font-bold text-white">2. Valores</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              label="Lance inicial (R$)"
              inputMode="decimal"
              autoComplete="off"
              placeholder="1000,00"
              value={startingBid}
              onChange={(event) => setStartingBid(event.target.value)}
              error={touched ? errors.starting_bid : undefined}
              hint="O primeiro lance tem de ser pelo menos este valor."
            />
            <FormField
              label="Incremento mínimo (R$)"
              inputMode="decimal"
              autoComplete="off"
              placeholder="50,00"
              value={increment}
              onChange={(event) => setIncrement(event.target.value)}
              error={touched ? errors.min_increment : undefined}
              hint="Cada lance seguinte sobe pelo menos este valor."
            />
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="text-lg font-bold text-white">3. Duração</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              label="Início"
              type="datetime-local"
              value={startsAt}
              onChange={(event) => setStartsAt(event.target.value)}
              error={touched ? errors.starts_at : undefined}
              hint="Pode ser agora: o lote fica logo ao vivo."
            />
            <FormField
              label="Fim"
              type="datetime-local"
              value={endsAt}
              onChange={(event) => setEndsAt(event.target.value)}
              error={touched ? errors.ends_at : undefined}
              hint="Um lance nos últimos 2 minutos prolonga o fim em 2 minutos."
            />
          </div>
          <div className="flex flex-wrap items-center gap-2" aria-label="Durações rápidas">
            <span className="text-sm text-neutral-500">Duração:</span>
            {DURATIONS.map((duration) => (
              <button
                key={duration.label}
                type="button"
                onClick={() => setDuration(duration.ms)}
                className="rounded border border-neutral-800 px-3 py-1.5 text-sm text-neutral-300 hover:border-primary/60 hover:text-white"
              >
                {duration.label}
              </button>
            ))}
          </div>
        </section>

        {valid && (
          <p className="rounded border border-neutral-800 bg-background-elevated p-3 text-sm text-neutral-300">
            <strong className="text-white">{item.title}</strong> abre com {formatMoney(starting)} (incrementos de{" "}
            {formatMoney(step)}), de {formatDateTime(startsIso)} a {formatDateTime(endsIso)}.
          </p>
        )}

        {createLot.isError && !Object.keys(apiFields).length && <Alert>{createLot.error.message}</Alert>}

        <div className="flex gap-2">
          <Button type="submit" disabled={createLot.isPending} className="disabled:opacity-50">
            {createLot.isPending ? "A criar…" : "Criar lote"}
          </Button>
          <Link href="/painel" className="inline-flex items-center px-4 text-neutral-400 hover:text-white">
            Cancelar
          </Link>
        </div>
      </form>
    </div>
  );
}

function CatalogPicker({ onPick }: { onPick: (item: CatalogItem) => void }) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const filter = useDebouncedValue(search.trim(), 400);
  const { data, isFetching, isError, error, isPlaceholderData } = useCatalogSearchQuery(filter, page);

  return (
    <div className="space-y-4">
      <Input
        type="search"
        value={search}
        onChange={(event) => {
          setSearch(event.target.value);
          setPage(1);
        }}
        placeholder="Pesquisar no catálogo do museu (ex.: Monet, paisagem, retrato)"
        aria-label="Pesquisar no catálogo do museu"
        maxLength={100}
        icon={<Search size={16} className="text-neutral-500" aria-hidden="true" />}
      />

      {filter.length < 2 ? (
        <p className="text-sm text-neutral-500">Escreva pelo menos 2 letras para pesquisar.</p>
      ) : isError ? (
        <Alert>
          {toApiError(error).message} As obras já em leilão continuam a funcionar; tente de novo daqui a pouco.
        </Alert>
      ) : !data ? (
        <p className="text-sm text-neutral-400">A pesquisar…</p>
      ) : data.data.length === 0 ? (
        <p className="text-sm text-neutral-400">Nenhuma obra com imagem encontrada para &quot;{filter}&quot;.</p>
      ) : (
        <div className={cn("space-y-4 transition-opacity", (isPlaceholderData || isFetching) && "opacity-60")}>
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {data.data.map((item) => (
              <li key={item.external_id}>
                <button
                  type="button"
                  onClick={() => onPick(item)}
                  className="group flex w-full flex-col overflow-hidden rounded-xl border border-neutral-900 bg-background-elevated text-left hover:border-primary/60 focus-visible:outline-2 focus-visible:outline-primary"
                >
                  <LotImage src={item.image_url} alt={item.title} sizes="(min-width: 1024px) 25vw, 50vw" className="aspect-4/3 w-full" />
                  <span className="flex items-start justify-between gap-2 p-3">
                    <span className="min-w-0">
                      <span className="line-clamp-1 text-sm font-bold text-white">{item.title}</span>
                      <span className="line-clamp-1 text-xs text-neutral-400">
                        {[item.attributes.artist, item.attributes.date].filter(Boolean).join(" · ") || "Autor desconhecido"}
                      </span>
                    </span>
                    <Check size={16} className="mt-0.5 shrink-0 text-primary opacity-0 group-hover:opacity-100" aria-hidden="true" />
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <Pagination meta={data.meta} onPageChange={setPage} />
        </div>
      )}
    </div>
  );
}
