"use client";

import { useId } from "react";
import type { ComponentProps } from "react";
import { Input } from "./input";

type FormFieldProps = ComponentProps<typeof Input> & {
  label: string;
  error?: string;
  hint?: string;
};

export function FormField({ label, error, hint, id, ...props }: FormFieldProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const describedBy = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined;

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={inputId} className="text-sm text-neutral-300">
        {label}
      </label>
      <Input
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        containerClassName={`bg-neutral-900 ${error ? "border-red-500/70" : "border-neutral-800"}`}
        {...props}
      />
      {error ? (
        <p id={`${inputId}-error`} className="text-xs text-red-400">
          {error}
        </p>
      ) : hint ? (
        <p id={`${inputId}-hint`} className="text-xs text-neutral-500">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
