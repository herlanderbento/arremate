"use client";

import { ImageOff } from "lucide-react";
import Image from "next/image";
import { useState } from "react";
import { cn, museumImageSrc } from "@/lib";

type LotImageProps = {
  src: string | null;
  alt: string;
  sizes: string;
  priority?: boolean;
  className?: string;
};

export function LotImage({ src, alt, sizes, priority, className }: LotImageProps) {
  const [attempt, setAttempt] = useState(0);
  const failed = attempt > 1;

  const retryOnce = () => {
    if (attempt === 0) setTimeout(() => setAttempt(1), 3000);
    else setAttempt(2);
  };

  return (
    <div className={cn("relative overflow-hidden bg-neutral-900", className)}>
      {src && !failed ? (
        <Image
          key={attempt}
          src={attempt === 0 ? museumImageSrc(src) : `${museumImageSrc(src)}?retry=1`}
          alt={alt}
          fill
          sizes={sizes}
          priority={priority}
          unoptimized
          className="object-cover"
          onError={retryOnce}
        />
      ) : (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-neutral-600">
          <ImageOff size={28} aria-hidden="true" />
          <span className="text-xs">Imagem indisponível</span>
        </div>
      )}
    </div>
  );
}
