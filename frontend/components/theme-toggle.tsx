"use client";

import { Moon, Sun } from "lucide-react";
import { useSyncExternalStore } from "react";
import { THEME_STORAGE_KEY } from "@/lib";
import type { Theme } from "@/lib";

function subscribe(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => observer.disconnect();
}

const getTheme = () => (document.documentElement.dataset.theme === "light" ? "light" : "dark") as Theme;

export function ThemeToggle({ className = "" }: { className?: string }) {
  const theme = useSyncExternalStore<Theme | null>(subscribe, getTheme, () => null);
  const next: Theme = theme === "light" ? "dark" : "light";

  const toggle = () => {
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {}
  };

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={next === "light" ? "Mudar para o tema claro" : "Mudar para o tema escuro"}
      title={next === "light" ? "Tema claro" : "Tema escuro"}
      className={`rounded p-2 text-neutral-400 hover:text-white ${className}`}
    >
      {theme === "light" ? <Moon size={18} aria-hidden="true" /> : <Sun size={18} aria-hidden="true" />}
    </button>
  );
}
