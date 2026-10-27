"use client";

import { ArrowLeft, Link2, RefreshCw, ShieldAlert, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { Alert, Button, ButtonLink } from "@/components";
import { useLotAuditQuery } from "@/hooks";
import { cn, formatDateTime, formatMoney, toApiError } from "@/lib";
import type { IntegrityReason } from "@/types";

const REASON: Record<IntegrityReason, string> = {
  SEQ_GAP: "Falta um lance na sequência: um lance foi apagado.",
  PREV_HASH_MISMATCH: "Este lance não está ligado ao anterior: foi inserido ou reordenado.",
  HASH_MISMATCH: "O conteúdo deste lance (valor, licitante ou hora) foi alterado.",
  CHAIN_HEAD_MISMATCH: "O selo do lote não corresponde à cadeia: lances foram removidos ou acrescentados no fim.",
  LOT_STATE_MISMATCH: "O lance atual ou o número de lances do lote não batem com o histórico.",
  RECEIPT_MISMATCH: "O comprovativo emitido não corresponde ao histórico.",
};

const short = (hash: string) => `${hash.slice(0, 10)}…${hash.slice(-6)}`;

export function AuditView({ lotId }: { lotId: string }) {
  const { data: audit, isPending, isError, error, refetch, isFetching, dataUpdatedAt } = useLotAuditQuery(lotId);

  if (isPending) {
    return <p className="container py-20 text-center text-neutral-400">A verificar o histórico…</p>;
  }
  if (isError) {
    const apiError = toApiError(error);
    return (
      <div className="container max-w-lg space-y-4 py-20 text-center">
        <Alert>{apiError.status === 404 || apiError.status === 422 ? "Lote não encontrado." : apiError.message}</Alert>
        <ButtonLink href="/" variant="outline">
          Voltar à vitrine
        </ButtonLink>
      </div>
    );
  }

  const intact = audit.status === "INTACT";
  const lotIssues = audit.issues.filter((issue) => issue.seq === null);
  const issuesBySeq = new Map<number, IntegrityReason[]>();
  for (const issue of audit.issues) {
    if (issue.seq !== null) issuesBySeq.set(issue.seq, [...(issuesBySeq.get(issue.seq) ?? []), issue.reason]);
  }

  return (
    <div className="container max-w-4xl space-y-6 py-10">
      <Link href={`/lotes/${audit.lot_id}`} className="inline-flex items-center gap-1.5 text-sm text-neutral-400 hover:text-white">
        <ArrowLeft size={16} aria-hidden="true" />
        Voltar ao lote
      </Link>

      <header className="space-y-1">
        <p className="text-sm text-neutral-500">Auditoria do histórico de lances</p>
        <h1 className="text-3xl font-extrabold text-white">{audit.title}</h1>
      </header>

      <section
        role="status"
        className={cn(
          "flex flex-col gap-4 rounded-xl border p-5 sm:flex-row sm:items-center sm:justify-between",
          intact ? "border-emerald-500/40 bg-emerald-500/10" : "border-red-500/50 bg-red-500/10"
        )}
      >
        <div className="flex items-start gap-3">
          {intact ? (
            <ShieldCheck size={32} className="shrink-0 text-emerald-300" aria-hidden="true" />
          ) : (
            <ShieldAlert size={32} className="shrink-0 text-red-300" aria-hidden="true" />
          )}
          <div>
            <p className={cn("text-xl font-extrabold", intact ? "text-emerald-200" : "text-red-200")}>
              {intact ? "Histórico íntegro" : "Histórico adulterado"}
            </p>
            <p className="text-sm text-neutral-300">
              {intact
                ? `Os ${audit.bids.length} lances foram verificados um a um e nenhum foi alterado, apagado ou reordenado.`
                : `Foram encontrados ${audit.issues.length} ${audit.issues.length === 1 ? "problema" : "problemas"}.`}
            </p>
            <p className="text-xs text-neutral-500">Verificado em {formatDateTime(new Date(dataUpdatedAt).toISOString())}</p>
          </div>
        </div>
        <Button
          variant="outline"
          onClick={() => refetch()}
          disabled={isFetching}
          className="shrink-0 whitespace-nowrap px-4 py-2 text-sm disabled:opacity-50"
        >
          <RefreshCw size={16} className={isFetching ? "animate-spin" : undefined} aria-hidden="true" />
          Verificar de novo
        </Button>
      </section>

      {lotIssues.length > 0 && (
        <ul className="space-y-2">
          {lotIssues.map((issue) => (
            <li key={issue.reason}>
              <Alert>{REASON[issue.reason]}</Alert>
            </li>
          ))}
        </ul>
      )}

      <section className="space-y-3">
        <h2 className="font-bold text-white">Cadeia de lances</h2>
        {audit.bids.length === 0 ? (
          <p className="rounded-xl border border-neutral-900 bg-background-elevated p-5 text-sm text-neutral-500">
            Este lote ainda não tem lances.
          </p>
        ) : (
          <ol className="space-y-2">
            {audit.bids.map((bid) => {
              const problems = issuesBySeq.get(bid.seq) ?? [];
              const ok = bid.valid && problems.length === 0;
              return (
                <li
                  key={bid.seq}
                  className={cn(
                    "space-y-2 rounded-xl border bg-background-elevated p-4 text-sm",
                    ok ? "border-neutral-900" : "border-red-500/50"
                  )}
                >
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                    <span className="font-semibold tabular-nums text-neutral-400">#{bid.seq}</span>
                    <span className="text-neutral-200">{bid.bidder_alias}</span>
                    <span className="font-semibold tabular-nums text-white">{formatMoney(bid.amount)}</span>
                    <time dateTime={bid.created_at} className="text-xs text-neutral-500">
                      {formatDateTime(bid.created_at)}
                    </time>
                    <span className={cn("ml-auto text-xs font-semibold", ok ? "text-emerald-300" : "text-red-300")}>
                      {ok ? "✓ válido" : "✗ inválido"}
                    </span>
                  </div>
                  <p className="flex items-center gap-1.5 font-mono text-xs text-neutral-500" title={bid.hash}>
                    <Link2 size={12} aria-hidden="true" />
                    {short(bid.hash)}
                  </p>
                  {problems.map((reason) => (
                    <p key={reason} className="text-xs text-red-200">
                      {REASON[reason]}
                    </p>
                  ))}
                </li>
              );
            })}
          </ol>
        )}
        <div className="space-y-1">
          <p className="text-xs text-neutral-500">Selo atual do lote (chain head)</p>
          <p className="break-all rounded bg-neutral-900 p-3 font-mono text-xs text-neutral-300">{audit.chain_head}</p>
        </div>
      </section>

      <section className="space-y-2 rounded-xl border border-neutral-900 bg-background-elevated p-5 text-sm text-neutral-400">
        <h2 className="font-bold text-white">Como funciona</h2>
        <p>
          Cada lance guarda um <strong className="text-neutral-200">hash</strong> (HMAC-SHA256) calculado sobre o seu
          conteúdo (lote, número, licitante, valor, hora) <em>e</em> sobre o hash do lance anterior. Os lances ficam assim
          encadeados: mudar um valor antigo muda o seu hash e quebra a ligação com todos os seguintes.
        </p>
        <p>
          O lote guarda ainda um <strong className="text-neutral-200">selo</strong> (chain head) que resume a cadeia
          inteira e o número de lances, por isso também se deteta apagar o último lance. A chave do HMAC fica só no
          servidor, fora da base de dados: quem alterar a base não consegue recalcular hashes válidos.
        </p>
        <p>Esta verificação refaz todos os cálculos a cada pedido. Os licitantes aparecem só por pseudónimo.</p>
      </section>
    </div>
  );
}
