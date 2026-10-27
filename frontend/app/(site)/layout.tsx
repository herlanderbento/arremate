import { Suspense } from "react";
import { Footer, Header, HeaderFallback } from "@/components";

export default function SiteLayout({ children }: LayoutProps<"/">) {
  return (
    <>
      <Suspense fallback={<HeaderFallback />}>
        <Header />
      </Suspense>
      <main className="flex-1">{children}</main>
      <Footer />
    </>
  );
}
