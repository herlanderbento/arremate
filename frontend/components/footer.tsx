import Link from "next/link";
import { Logo } from "./logo";

const LINKS = [
  { href: "/", label: "Vitrine" },
  { href: "/carteira", label: "Carteira" },
  { href: "/meus-arremates", label: "Meus arremates" },
  { href: "/painel", label: "Painel do leiloeiro" },
];

export function Footer() {
  return (
    <footer className="mt-24 border-t border-neutral-900 print:hidden">
      <div className="container flex flex-col gap-6 py-10 md:flex-row md:items-center md:justify-between">
        <div className="space-y-2">
          <Logo />
          <p className="max-w-md text-sm text-neutral-500">
            Leilões de obras do Art Institute of Chicago. Saldo simulado, sem dinheiro real.
          </p>
        </div>
        <nav aria-label="Rodapé" className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-neutral-400">
          {LINKS.map((link) => (
            <Link key={link.href} href={link.href} className="hover:text-white">
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
    </footer>
  );
}
