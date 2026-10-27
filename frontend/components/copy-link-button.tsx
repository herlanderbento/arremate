"use client";

import { Check, Link2 } from "lucide-react";
import { useState } from "react";
import { Button } from "./button";

type CopyLinkButtonProps = {
  path: string;
  label?: string;
  variant?: "primary" | "outline" | "ghost";
  className?: string;
};

function copyWithTextarea(text: string) {
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

export function CopyLinkButton({ path, label = "Copiar link", variant = "outline", className = "" }: CopyLinkButtonProps) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    const url = `${window.location.origin}${path}`;
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      copyWithTextarea(url);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Button variant={variant} onClick={copy} className={className} aria-live="polite">
      {copied ? <Check size={16} aria-hidden="true" /> : <Link2 size={16} aria-hidden="true" />}
      {copied ? "Link copiado" : label}
    </Button>
  );
}
