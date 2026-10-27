import { ChevronLeft, ChevronRight } from "lucide-react";
import type { PageMeta } from "@/types";

type PaginationProps = {
  meta: PageMeta;
  onPageChange: (page: number) => void;
};

export function Pagination({ meta, onPageChange }: PaginationProps) {
  if (meta.last_page <= 1) return null;
  const { current_page: page, last_page: last } = meta;
  const buttonClass =
    "inline-flex items-center gap-1 rounded border border-neutral-800 px-3 py-2 text-sm text-neutral-300 hover:border-neutral-600 disabled:pointer-events-none disabled:opacity-40";

  return (
    <nav aria-label="Paginação" className="flex items-center justify-center gap-3">
      <button type="button" className={buttonClass} disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
        <ChevronLeft size={16} aria-hidden="true" />
        Anterior
      </button>
      <span className="text-sm text-neutral-400 tabular-nums">
        Página {page} de {last}
      </span>
      <button type="button" className={buttonClass} disabled={page >= last} onClick={() => onPageChange(page + 1)}>
        Seguinte
        <ChevronRight size={16} aria-hidden="true" />
      </button>
    </nav>
  );
}
