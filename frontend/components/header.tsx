"use client";

import { LogOut, Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { useLogoutMutation, useMeQuery } from "@/hooks";
import { cn } from "@/lib";
import type { User, UserRole } from "@/types";
import { ButtonLink } from "./button";
import { Logo } from "./logo";
import { ThemeToggle } from "./theme-toggle";

type NavItem = { href: string; label: string };

const PUBLIC_NAV: NavItem[] = [{ href: "/", label: "Vitrine" }];

const ROLE_NAV: Record<UserRole, NavItem[]> = {
  BIDDER: [
    { href: "/carteira", label: "Carteira" },
    { href: "/meus-arremates", label: "Meus arremates" },
  ],
  AUCTIONEER: [
    { href: "/painel", label: "Painel do leiloeiro" },
    { href: "/painel/novo", label: "Novo lote" },
  ],
};

const ROLE_BADGE: Record<UserRole, string> = {
  AUCTIONEER: "Leiloeiro",
  BIDDER: "Licitante",
};

function navFor(user: User | null | undefined): NavItem[] {
  return user ? [...PUBLIC_NAV, ...ROLE_NAV[user.role]] : PUBLIC_NAV;
}

function matches(pathname: string, href: string) {
  if (href === "/") return pathname === "/" || pathname.startsWith("/lotes");
  return pathname === href || pathname.startsWith(`${href}/`);
}

function activeHref(pathname: string, items: NavItem[]) {
  return items
    .filter((item) => matches(pathname, item.href))
    .sort((a, b) => b.href.length - a.href.length)[0]?.href;
}

export function Header() {
  const { data: user, isPending } = useMeQuery();
  const logout = useLogoutMutation();
  const router = useRouter();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const items = navFor(user);
  const active = activeHref(pathname, items);

  const signOut = () => {
    setMenuOpen(false);
    logout.mutate(undefined, { onSettled: () => router.push("/") });
  };

  const navLink = (item: NavItem, className: string) => (
    <Link
      key={item.href}
      href={item.href}
      onClick={() => setMenuOpen(false)}
      aria-current={item.href === active ? "page" : undefined}
      className={cn(className, item.href === active ? "text-primary" : "text-neutral-300 hover:text-white")}
    >
      {item.label}
    </Link>
  );

  return (
    <header className="sticky top-0 z-20 border-b border-neutral-900 bg-background/80 backdrop-blur print:hidden">
      <div className="container flex h-16 items-center justify-between gap-6">
        <div className="flex items-center gap-8">
          <Logo />
          <nav aria-label="Principal" className="hidden md:flex items-center gap-6 text-sm font-medium">
            {items.map((item) => navLink(item, ""))}
          </nav>
        </div>

        <div className="hidden md:flex items-center gap-4 text-sm">
          <ThemeToggle />
          {isPending ? null : user ? (
            <>
              <span className="text-neutral-300">
                {user.name}{" "}
                <span className="ml-1 rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-400">
                  {ROLE_BADGE[user.role]}
                </span>
              </span>
              <button
                type="button"
                onClick={signOut}
                className="inline-flex items-center gap-1.5 text-neutral-400 hover:text-white"
              >
                <LogOut size={16} aria-hidden="true" />
                Sair
              </button>
            </>
          ) : (
            <>
              <ButtonLink href={`/login?next=${encodeURIComponent(pathname)}`} variant="ghost" className="px-4 py-2">
                Entrar
              </ButtonLink>
              <ButtonLink href="/registo" className="px-4 py-2">
                Criar conta
              </ButtonLink>
            </>
          )}
        </div>

        <div className="flex items-center gap-1 md:hidden">
          <ThemeToggle />
          <button
            type="button"
            className="rounded p-2 text-neutral-300 hover:text-white"
            aria-label={menuOpen ? "Fechar menu" : "Abrir menu"}
            aria-expanded={menuOpen}
            aria-controls="mobile-menu"
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {menuOpen && (
        <div id="mobile-menu" className="md:hidden border-t border-neutral-900 bg-background">
          <nav aria-label="Principal" className="container flex flex-col py-2 text-base font-medium">
            {items.map((item) => navLink(item, "py-3"))}
          </nav>
          <div className="container border-t border-neutral-900 py-4">
            {isPending ? null : user ? (
              <div className="flex items-center justify-between gap-4 text-sm">
                <span className="text-neutral-300">
                  {user.name}{" "}
                  <span className="ml-1 rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-400">
                    {ROLE_BADGE[user.role]}
                  </span>
                </span>
                <button
                  type="button"
                  onClick={signOut}
                  className="inline-flex items-center gap-1.5 text-neutral-400 hover:text-white"
                >
                  <LogOut size={16} aria-hidden="true" />
                  Sair
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                <ButtonLink
                  href={`/login?next=${encodeURIComponent(pathname)}`}
                  variant="outline"
                  className="px-4 py-2"
                  onClick={() => setMenuOpen(false)}
                >
                  Entrar
                </ButtonLink>
                <ButtonLink href="/registo" className="px-4 py-2" onClick={() => setMenuOpen(false)}>
                  Criar conta
                </ButtonLink>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
}

export function HeaderFallback() {
  return (
    <header className="sticky top-0 z-20 border-b border-neutral-900 bg-background/80 backdrop-blur print:hidden">
      <div className="container flex h-16 items-center">
        <Logo />
      </div>
    </header>
  );
}
