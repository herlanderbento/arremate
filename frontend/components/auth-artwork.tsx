"use client";

import Image from "next/image";
import { usePathname } from "next/navigation";

const ARTWORKS = {
  login: {
    src: "/auth/login.jpg",
    title: "Paris Street; Rainy Day",
    artist: "Gustave Caillebotte, 1877",
    position: "object-[70%_center]",
  },
  registo: {
    src: "/auth/registo.jpg",
    title: "Two Sisters (On the Terrace)",
    artist: "Pierre-Auguste Renoir, 1881",
    position: "object-center",
  },
};

export function AuthArtwork() {
  const artwork = usePathname().startsWith("/registo") ? ARTWORKS.registo : ARTWORKS.login;

  return (
    <div className="relative hidden overflow-hidden bg-[#0e0e11] md:block">
      <Image
        key={artwork.src}
        src={artwork.src}
        alt={`${artwork.title}, de ${artwork.artist}`}
        fill
        priority
        sizes="50vw"
        className={`object-cover ${artwork.position}`}
      />
      <div className="absolute inset-0 bg-linear-to-t from-[#000]/90 via-[#000]/40 to-transparent" />
      <div className="absolute inset-x-0 bottom-0 space-y-4 p-12">
        <p className="max-w-md text-3xl font-bold text-[#fff]">
          Obras de arte, lances ao vivo e um histórico que ninguém consegue adulterar.
        </p>
        <p className="max-w-md text-[#d4d4d4]">
          Acompanhe cada lote em tempo real e audite qualquer leilão, mesmo sem conta.
        </p>
        <p className="text-xs text-[#a3a3a3]">
          {artwork.title} · {artwork.artist} · Art Institute of Chicago
        </p>
      </div>
    </div>
  );
}

export function AuthArtworkFallback() {
  return <div className="hidden bg-gradient-dark md:block" />;
}
