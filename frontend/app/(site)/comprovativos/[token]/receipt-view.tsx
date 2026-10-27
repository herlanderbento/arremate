"use client";

import { BadgeCheck, Printer, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { Alert, Button, ButtonLink, CopyLinkButton, LotImage } from "@/components";
import { useReceiptQuery } from "@/hooks";
import { formatDateTime, formatMoney, toApiError } from "@/lib";

export function ReceiptView({ token }: { token: string }) {
  const { data: receipt, isPending, isError, error } = useReceiptQuery(token);

  if (isPending) {
    return <p className="container py-20 text-center text-neutral-400">A carregar o comprovativo…</p>;
  }
  if (isError) {
    const apiError = toApiError(error);
    return (
      <div className="container max-w-lg space-y-4 py-20 text-center">
        <Alert>{apiError.status === 404 || apiError.status === 422 ? "Comprovativo não encontrado." : apiError.message}</Alert>
        <ButtonLink href="/" variant="outline">
          Voltar à vitrine
        </ButtonLink>
      </div>
    );
  }

  return (
    <div className="container max-w-2xl py-10">
      <article className="overflow-hidden rounded-xl border border-neutral-900 bg-background-elevated print:border-[#d4d4d4] print:bg-[#fff] print:text-[#000]">
        <LotImage src={receipt.image_url} alt={receipt.title} sizes="672px" className="aspect-video" />

        <div className="space-y-6 p-6">
          <header className="space-y-2">
            <p className="flex items-center gap-2 text-sm font-semibold text-primary print:text-[#000]">
              <BadgeCheck size={18} aria-hidden="true" />
              Comprovativo de arremate
            </p>
            <h1 className="text-2xl font-extrabold text-white print:text-[#000]">{receipt.title}</h1>
          </header>

          <dl className="grid gap-4 text-sm sm:grid-cols-2">
            <Field label="Arrematante" value={receipt.winner_alias} />
            <Field label="Valor de arremate" value={formatMoney(receipt.amount)} strong />
            <Field label="Emitido em" value={formatDateTime(receipt.issued_at)} />
            <Field label="Lances no leilão" value={String(receipt.bid_count)} />
          </dl>

          <div className="space-y-1">
            <p className="text-xs text-neutral-500">Selo do histórico (chain head)</p>
            <p className="break-all rounded bg-neutral-900 p-3 font-mono text-xs text-neutral-300 print:bg-[#f5f5f5] print:text-[#000]">
              {receipt.chain_head}
            </p>
            <p className="text-xs text-neutral-500">
              Este selo resume toda a sequência de lances do lote. Se algum lance for alterado, apagado ou reordenado, a
              verificação do histórico deixa de bater com ele.
            </p>
          </div>

          <div className="flex flex-wrap gap-2 print:hidden">
            <CopyLinkButton path={`/comprovativos/${token}`} variant="primary" className="px-4 py-2 text-sm" />
            <Button variant="outline" onClick={() => window.print()} className="px-4 py-2 text-sm">
              <Printer size={16} aria-hidden="true" />
              Imprimir
            </Button>
            <ButtonLink href={`/auditoria/${receipt.lot_id}`} className="px-4 py-2 text-sm">
              <ShieldCheck size={16} aria-hidden="true" />
              Verificar integridade
            </ButtonLink>
            <ButtonLink href={`/lotes/${receipt.lot_id}`} variant="ghost" className="px-4 py-2 text-sm">
              Ver o lote
            </ButtonLink>
          </div>
          <p className="text-xs text-neutral-500 print:hidden">
            O arrematante aparece só pelo pseudónimo do lote: o comprovativo não contém nome nem e-mail.{" "}
            <Link href="/meus-arremates" className="hover:underline">
              Meus arremates
            </Link>
          </p>
        </div>
      </article>
    </div>
  );
}

function Field({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div>
      <dt className="text-xs text-neutral-500">{label}</dt>
      <dd className={strong ? "text-lg font-extrabold text-primary print:text-[#000]" : "font-medium text-neutral-200 print:text-[#000]"}>
        {value}
      </dd>
    </div>
  );
}
