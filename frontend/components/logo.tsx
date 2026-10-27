import { Gavel } from "lucide-react";
import Link from "next/link";

export function Logo({ className = "" }: { className?: string }) {
  return (
    <Link
      href="/"
      aria-label="Arremate, página inicial"
      className={`inline-flex items-center gap-2 text-xl font-extrabold tracking-tight text-white ${className}`}
    >
      <Gavel size={22} className="text-primary" aria-hidden="true" />
      Arremate
    </Link>
  );
}
