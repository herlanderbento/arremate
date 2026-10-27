"use client";

import { Lock, PiggyBank, Wallet as WalletIcon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { Alert, Button, Input, RequireAuth } from "@/components";
import { useDepositMutation, useMyBidsQuery, useWalletQuery } from "@/hooks";
import { formatMoney, parseMoneyInput, toApiError } from "@/lib";
import type { Wallet } from "@/types";

const QUICK_AMOUNTS = ["100.00", "500.00", "1000.00", "5000.00"];

export default function WalletPage() {
  return <RequireAuth role="BIDDER">{() => <WalletContent />}</RequireAuth>;
}

function WalletContent() {
  const { data: wallet, isPending, isError, error } = useWalletQuery();

  return (
    <div className="container max-w-4xl space-y-8 py-10">
      <section className="space-y-2">
        <h1 className="text-3xl font-extrabold text-white">Carteira</h1>
        <p className="text-neutral-400">
          Saldo simulado para licitar. Enquanto um lance seu lidera, o valor fica comprometido e não pode ser usado
          noutro lote; se for superado, volta logo a ficar disponível.
        </p>
      </section>

      {isError ? (
        <Alert>{toApiError(error).message}</Alert>
      ) : (
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard icon={<WalletIcon size={18} />} label="Saldo total" value={wallet?.balance} loading={isPending} />
          <StatCard icon={<Lock size={18} />} label="Comprometido em lances" value={wallet?.committed} loading={isPending} />
          <StatCard
            icon={<PiggyBank size={18} />}
            label="Disponível para licitar"
            value={wallet?.available}
            loading={isPending}
            highlight
          />
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <DepositForm />
        {wallet && <CommittedLots wallet={wallet} />}
      </div>
    </div>
  );
}

type StatCardProps = { icon: ReactNode; label: string; value: string | undefined; loading: boolean; highlight?: boolean };

function StatCard({ icon, label, value, loading, highlight }: StatCardProps) {
  return (
    <div className="rounded-xl border border-neutral-900 bg-background-elevated p-5">
      <p className="flex items-center gap-2 text-sm text-neutral-400">
        <span className="text-neutral-500" aria-hidden="true">
          {icon}
        </span>
        {label}
      </p>
      {loading ? (
        <div className="mt-2 h-8 w-32 animate-pulse rounded bg-neutral-900" />
      ) : (
        <p className={`mt-1 text-2xl font-extrabold tabular-nums ${highlight ? "text-primary" : "text-white"}`}>
          {formatMoney(value)}
        </p>
      )}
    </div>
  );
}

function DepositForm() {
  const deposit = useDepositMutation();
  const [value, setValue] = useState("");
  const [deposited, setDeposited] = useState<string | null>(null);
  const amount = parseMoneyInput(value);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!amount || deposit.isPending) return;
    deposit.mutate(amount, {
      onSuccess: () => {
        setDeposited(amount);
        setValue("");
      },
    });
  };

  return (
    <form onSubmit={submit} className="space-y-4 rounded-xl border border-neutral-900 bg-background-elevated p-5" noValidate>
      <div>
        <h2 className="font-bold text-white">Depositar</h2>
        <p className="text-sm text-neutral-500">Dinheiro fictício, até {formatMoney("100000")} por depósito.</p>
      </div>

      <div className="flex flex-wrap gap-2" aria-label="Valores rápidos">
        {QUICK_AMOUNTS.map((quick) => (
          <button
            key={quick}
            type="button"
            onClick={() => setValue(quick.replace(".", ","))}
            className="rounded border border-neutral-800 px-3 py-1.5 text-sm text-neutral-300 hover:border-primary/60 hover:text-white"
          >
            {formatMoney(quick)}
          </button>
        ))}
      </div>

      <div className="flex gap-2">
        <Input
          inputMode="decimal"
          autoComplete="off"
          placeholder="0,00"
          aria-label="Valor do depósito"
          value={value}
          onChange={(event) => {
            setValue(event.target.value);
            setDeposited(null);
          }}
          aria-invalid={value !== "" && !amount}
          containerClassName="flex-1"
          icon={<span className="text-sm text-neutral-500">R$</span>}
        />
        <Button type="submit" disabled={!amount || deposit.isPending} className="px-5 disabled:opacity-50">
          {deposit.isPending ? "A depositar…" : "Depositar"}
        </Button>
      </div>
      {value !== "" && !amount && (
        <p className="text-xs text-red-300">Indique um valor positivo, com até 2 casas decimais.</p>
      )}

      {deposit.isError && <Alert>{deposit.error.message}</Alert>}
      {deposited && !deposit.isError && <Alert variant="success">Depósito de {formatMoney(deposited)} efetuado.</Alert>}
    </form>
  );
}

function CommittedLots({ wallet }: { wallet: Wallet }) {
  const { data } = useMyBidsQuery({ per_page: 50 }, Number(wallet.committed) > 0);
  const leading = data?.data.filter((bid) => bid.situation === "winning") ?? [];

  return (
    <section className="space-y-3 rounded-xl border border-neutral-900 bg-background-elevated p-5">
      <h2 className="font-bold text-white">Valores comprometidos</h2>
      {Number(wallet.committed) === 0 ? (
        <p className="text-sm text-neutral-500">
          Nada comprometido. Os seus lances só reservam saldo enquanto lideram.{" "}
          <Link href="/" className="text-primary hover:underline">
            Ver leilões ao vivo
          </Link>
        </p>
      ) : (
        <ul className="divide-y divide-neutral-900 text-sm">
          {leading.map((bid) => (
            <li key={bid.id} className="flex items-center justify-between gap-3 py-2">
              <Link href={`/lotes/${bid.id}`} className="truncate text-neutral-300 hover:text-white">
                {bid.title}
              </Link>
              <span className="tabular-nums text-white">{formatMoney(bid.my_max_bid)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
