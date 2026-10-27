"use client";

import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";
import type { InputHTMLAttributes, ReactNode } from "react";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  icon?: ReactNode;
  containerClassName?: string;
};

export function Input({
  icon,
  containerClassName = "",
  className = "",
  type = "text",
  ...props
}: InputProps) {
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === "password";

  return (
    <div
      className={`flex items-center px-3 rounded border border-neutral-700 transition-colors focus-within:border-primary/60 ${containerClassName}`}
    >
      {icon}
      <input
        type={isPassword && showPassword ? "text" : type}
        className={`w-full p-3 outline-none bg-transparent placeholder:text-neutral-500 text-neutral-200 ${className}`}
        {...props}
      />
      {isPassword && (
        <button
          type="button"
          onClick={() => setShowPassword((value) => !value)}
          aria-label={showPassword ? "Hide password" : "Show password"}
          aria-pressed={showPassword}
          className="shrink-0 p-1 text-neutral-400 hover:text-white transition-colors rounded"
        >
          {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
        </button>
      )}
    </div>
  );
}
