"use client";

import { Alert, Button, FormField, Logo } from "@/components";
import { useLoginMutation } from "@/hooks";
import { afterLoginPath } from "@/lib";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

function LoginForm() {
  const router = useRouter();
  const next = useSearchParams().get("next");
  const login = useLoginMutation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    login.mutate(
      { email: email.trim(), password },
      { onSuccess: (user) => router.replace(afterLoginPath(user, next)) },
    );
  }

  return (
    <form className="space-y-4" onSubmit={submit} noValidate>
      {login.error && <Alert>{login.error.message}</Alert>}
      <FormField
        label="E-mail"
        type="email"
        autoComplete="email"
        placeholder="nome@exemplo.com"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
      />
      <FormField
        label="Senha"
        type="password"
        autoComplete="current-password"
        placeholder="A sua senha"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      <Button type="submit" className="w-full" disabled={login.isPending || !email || !password}>
        {login.isPending ? "A entrar…" : "Entrar"}
      </Button>
    </form>
  );
}

export default function Login() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col items-center justify-center gap-4 text-center">
        <Logo />
        <h1 className="text-3xl font-bold text-white">Entrar</h1>
      </div>
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
      <p className="text-center text-sm text-neutral-400">
        Ainda não tem conta?{" "}
        <Link href="/registo" className="text-primary hover:underline">
          Criar conta
        </Link>
      </p>
    </div>
  );
}
