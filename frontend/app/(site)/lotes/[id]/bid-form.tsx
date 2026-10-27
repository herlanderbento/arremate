"use client";

import { Gavel } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import type { FormEvent } from "react";
import { Alert, Button, ButtonLink, Input } from "@/components";
import { useMeQuery, usePlaceBidMutation } from "@/hooks";
import type { LotDetailView } from "@/hooks";
import { formatMoney, parseMoneyInput } from "@/lib";
import type { LotPhase } from "@/lib";
import type { PlaceBidResult } from "@/types";

const toInput = (amount: string) => amount.replace(".", ",");

const add = (amount: string, increment: string, times: number) =>
  (Number(amount) + Number(increment) * times).toFixed(2);

export function BidForm({ lot, phase }: { lot: LotDetailView; phase: LotPhase }) {
  const { data: user } = useMeQuery();
  const pathname = usePathname();
  const placeBid = usePlaceBidMutation(lot.id);
  const [typed, setTyped] = useState<string | null>(null);
  const [lastBid, setLastBid] = useState<PlaceBidResult | null>(null);

  if (phase !== "live") {
    const message: Record<Exclude<LotPhase, "live">, string> = {
      scheduled: "Os lances abrem quando o leilão começar.",
      closing: "O tempo acabou. A apurar o resultado…",
      ended: "Este leilão está encerrado.",
      cancelled: "Este leilão foi cancelado pelo leiloeiro. Os valores reservados foram devolvidos.",
    };
    return <p className="text-sm text-neutral-400">{message[phase]}</p>;
  }

  if (!user) {
    return (
      <div className="space-y-2">
        <ButtonLink href={`/login?next=${encodeURIComponent(pathname)}`} className="w-full">
          Entrar para dar lances
        </ButtonLink>
        <p className="text-center text-xs text-neutral-500">Qualquer pessoa pode acompanhar o leilão sem conta.</p>
      </div>
    );
  }

  if (user.role === "AUCTIONEER") {
    return <p className="text-sm text-neutral-400">Está a ver como leiloeiro: leiloeiros não podem dar lances.</p>;
  }

  if (lot.my_alias && lot.leader_alias === lot.my_alias) {
    return (
      <div className="space-y-3">
        {lastBid && (
          <Alert variant="success">
            Lance de {formatMoney(lastBid.amount)} registado. Saldo disponível: {formatMoney(lastBid.available)}.
            {lastBid.extended && " O leilão foi prolongado por causa do lance nos últimos minutos."}
          </Alert>
        )}
        <p className="text-sm text-neutral-400">
          O seu lance de {formatMoney(lot.current_bid)} lidera. Só pode licitar de novo quando alguém o superar.
        </p>
      </div>
    );
  }

  const value = typed ?? toInput(lot.min_next_bid);
  const amount = parseMoneyInput(value);
  const belowMinimum = amount !== null && Number(amount) < Number(lot.min_next_bid);
  const invalid = amount === null || belowMinimum;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (invalid || placeBid.isPending) return;
    placeBid.mutate(amount, {
      onSuccess: (bid) => {
        setLastBid(bid);
        setTyped(null);
      },
    });
  };

  return (
    <form onSubmit={submit} className="space-y-3" noValidate>
      <label htmlFor="bid-amount" className="block text-sm font-medium text-neutral-300">
        O seu lance (mínimo {formatMoney(lot.min_next_bid)})
      </label>
      <div className="flex gap-2">
        <Input
          id="bid-amount"
          inputMode="decimal"
          autoComplete="off"
          value={value}
          onChange={(event) => setTyped(event.target.value)}
          aria-invalid={invalid}
          aria-describedby="bid-hint"
          containerClassName="flex-1"
          icon={<span className="text-sm text-neutral-500">R$</span>}
        />
        <Button type="submit" disabled={invalid || placeBid.isPending} className="px-5 disabled:opacity-50">
          <Gavel size={18} aria-hidden="true" />
          {placeBid.isPending ? "A enviar…" : "Licitar"}
        </Button>
      </div>

      <div className="flex flex-wrap gap-2" aria-label="Valores rápidos">
        {[0, 1, 5].map((times) => {
          const quick = add(lot.min_next_bid, lot.min_increment, times);
          return (
            <button
              key={times}
              type="button"
              onClick={() => setTyped(toInput(quick))}
              className="rounded border border-neutral-800 px-2.5 py-1 text-xs text-neutral-300 hover:border-primary/60 hover:text-white"
            >
              {formatMoney(quick)}
            </button>
          );
        })}
      </div>

      <p id="bid-hint" className={belowMinimum || amount === null ? "text-xs text-red-300" : "text-xs text-neutral-500"}>
        {amount === null
          ? "Indique um valor válido, com até 2 casas decimais."
          : belowMinimum
            ? `O lance tem de ser de pelo menos ${formatMoney(lot.min_next_bid)}.`
            : "O valor fica reservado no seu saldo enquanto liderar; é devolvido se for superado."}
      </p>

      {placeBid.isError && (
        <Alert>
          {placeBid.error.message}
          {placeBid.error.code === "INSUFFICIENT_BALANCE" && (
            <>
              {" "}
              <Link href="/carteira" className="underline underline-offset-2 hover:text-white">
                Depositar na carteira
              </Link>
            </>
          )}
        </Alert>
      )}
    </form>
  );
}
