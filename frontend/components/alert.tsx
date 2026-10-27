import { CircleAlert, CircleCheck } from "lucide-react";
import type { ReactNode } from "react";

type AlertVariant = "error" | "success";

const styles: Record<AlertVariant, string> = {
  error: "border-red-500/40 bg-red-500/10 text-red-200",
  success: "border-emerald-500/40 bg-emerald-500/10 text-emerald-200",
};

export function Alert({ variant = "error", children }: { variant?: AlertVariant; children: ReactNode }) {
  const Icon = variant === "error" ? CircleAlert : CircleCheck;
  return (
    <div
      role={variant === "error" ? "alert" : "status"}
      className={`flex items-start gap-2 rounded border px-3 py-2.5 text-sm ${styles[variant]}`}
    >
      <Icon size={18} className="mt-0.5 shrink-0" aria-hidden="true" />
      <div>{children}</div>
    </div>
  );
}
