"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import type { ReactNode } from "react";
import { useMeQuery } from "@/hooks";
import type { User, UserRole } from "@/types";
import { ButtonLink } from "./button";

const ROLE_LABEL: Record<UserRole, string> = {
  AUCTIONEER: "leiloeiros",
  BIDDER: "licitantes",
};

type RequireAuthProps = {
  role?: UserRole;
  children: (user: User) => ReactNode;
};

export function RequireAuth({ role, children }: RequireAuthProps) {
  const { data: user, isPending, isError } = useMeQuery();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isPending && !isError && user === null) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [isPending, isError, user, router, pathname]);

  if (isPending || user === null) {
    return <p className="container py-20 text-center text-neutral-400">A carregar…</p>;
  }
  if (isError) {
    return (
      <p className="container py-20 text-center text-neutral-400">
        Não foi possível contactar o servidor. Tente novamente em instantes.
      </p>
    );
  }
  if (role && user.role !== role) {
    return (
      <div className="container py-20 text-center space-y-4">
        <p className="text-neutral-300">Esta área é só para {ROLE_LABEL[role]}.</p>
        <ButtonLink href="/" variant="outline">
          Voltar à vitrine
        </ButtonLink>
      </div>
    );
  }
  return <>{children(user)}</>;
}
