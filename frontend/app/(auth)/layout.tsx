import { ThemeToggle } from "@/components";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <main className="relative min-h-screen w-full grid md:grid-cols-2">
    <ThemeToggle className="absolute right-4 top-4" />
    <div className="flex flex-col items-center justify-center px-4 py-12">
      <div className="m-auto max-w-90.5 w-full">
        {children}
      </div>
    </div>
    <div className="hidden md:flex flex-col justify-end gap-4 p-12 bg-gradient-dark border-l border-neutral-900">
      <p className="text-3xl font-bold text-white max-w-md">
        Obras de arte, lances ao vivo e um histórico que ninguém consegue adulterar.
      </p>
      <p className="text-neutral-400 max-w-md">
        Acompanhe cada lote em tempo real e audite qualquer leilão, mesmo sem conta.
      </p>
    </div>
  </main>
}
