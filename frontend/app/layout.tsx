import type { Metadata } from "next";
import { Manrope } from "next/font/google";
import "./globals.css";
import { THEME_INIT_SCRIPT } from "@/lib";
import { QueryProvider } from "@/providers";

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Arremate",
  description: "Casa de leilões online de obras de arte, com lances ao vivo e histórico auditável.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="pt-BR"
      className={`${manrope.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="min-h-full flex flex-col">
        <QueryProvider>
          {children}
        </QueryProvider>
      </body>
    </html>
  );
}
