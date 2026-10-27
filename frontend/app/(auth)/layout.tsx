import { Suspense } from "react";
import { AuthArtwork, AuthArtworkFallback, ThemeToggle } from "@/components";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <main className="min-h-screen w-full grid md:grid-cols-2">
    <div className="relative flex flex-col items-center justify-center px-4 py-12">
      <ThemeToggle className="absolute right-4 top-4" />
      <div className="m-auto max-w-90.5 w-full">
        {children}
      </div>
    </div>
    <Suspense fallback={<AuthArtworkFallback />}>
      <AuthArtwork />
    </Suspense>
  </main>
}
