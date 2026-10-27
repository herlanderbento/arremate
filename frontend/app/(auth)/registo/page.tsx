"use client";

import { Alert, Button, FormField, Logo } from "@/components";
import { useRegisterMutation } from "@/hooks";
import { afterLoginPath, fieldErrors } from "@/lib";
import type { UserRole } from "@/types";
import { Gavel, HandCoins } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

const ROLES: { value: UserRole; title: string; description: string; Icon: typeof Gavel }[] = [
  {
    value: "BIDDER",
    title: "Licitante",
    description: "Deposita saldo, dá lances e arremata obras.",
    Icon: HandCoins,
  },
  {
    value: "AUCTIONEER",
    title: "Leiloeiro",
    description: "Cria e gere lotes. Não dá lances.",
    Icon: Gavel,
  },
];

const MIN_PASSWORD = 8;

export default function Register() {
  const router = useRouter();
  const register = useRegisterMutation();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("BIDDER");

  const errors = fieldErrors(register.error);
  const emailTaken = register.error?.code === "EMAIL_ALREADY_REGISTERED";
  const generalError =
    register.error && !emailTaken && register.error.code !== "VALIDATION_ERROR"
      ? register.error.message
      : null;

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    register.mutate(
      { name: name.trim(), email: email.trim(), password, role },
      { onSuccess: (user) => router.replace(afterLoginPath(user, null)) },
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-center justify-center gap-4 text-center">
        <Logo />
        <h1 className="text-3xl font-bold text-white">Criar conta</h1>
      </div>

      <form className="space-y-4" onSubmit={submit} noValidate>
        {generalError && <Alert>{generalError}</Alert>}

        <fieldset className="space-y-2">
          <legend className="text-sm text-neutral-300 mb-2">Como quer participar?</legend>
          <div className="grid grid-cols-2 gap-3">
            {ROLES.map(({ value, title, description, Icon }) => (
              <label
                key={value}
                className={`cursor-pointer rounded border p-3 transition-colors ${
                  role === value
                    ? "border-primary bg-primary/10"
                    : "border-neutral-800 bg-neutral-900 hover:border-neutral-700"
                }`}
              >
                <input
                  type="radio"
                  name="role"
                  value={value}
                  checked={role === value}
                  onChange={() => setRole(value)}
                  className="sr-only"
                />
                <Icon size={20} className={role === value ? "text-primary" : "text-neutral-400"} aria-hidden="true" />
                <span className="mt-2 block font-semibold text-white">{title}</span>
                <span className="block text-xs text-neutral-400">{description}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <FormField
          label="Nome"
          autoComplete="name"
          placeholder="O seu nome"
          value={name}
          onChange={(e) => setName(e.target.value)}
          error={errors.name}
          maxLength={120}
          required
        />
        <FormField
          label="E-mail"
          type="email"
          autoComplete="email"
          placeholder="nome@exemplo.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={emailTaken ? register.error?.message : errors.email}
          required
        />
        <FormField
          label="Senha"
          type="password"
          autoComplete="new-password"
          placeholder="Mínimo de 8 caracteres"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={errors.password}
          hint={`Pelo menos ${MIN_PASSWORD} caracteres.`}
          maxLength={72}
          required
        />

        <Button
          type="submit"
          className="w-full"
          disabled={register.isPending || !name.trim() || !email || password.length < MIN_PASSWORD}
        >
          {register.isPending ? "A criar conta…" : "Criar conta"}
        </Button>
      </form>

      <p className="text-center text-sm text-neutral-400">
        Já tem conta?{" "}
        <Link href="/login" className="text-primary hover:underline">
          Entrar
        </Link>
      </p>
    </div>
  );
}
