import Link from "next/link";
import type { ButtonHTMLAttributes, ComponentProps } from "react";

type ButtonVariant = "primary" | "outline" | "ghost";

const base =
  "inline-flex items-center justify-center font-bold gap-2 px-8 py-3 rounded border transition-colors";

const variants: Record<ButtonVariant, string> = {
  primary: "bg-primary text-background border-transparent hover:bg-primary/90",
  outline: "bg-transparent text-primary border-primary hover:bg-primary/10",
  ghost: "bg-transparent text-white border-transparent hover:bg-white/10",
};

export function buttonVariants(variant: ButtonVariant = "primary") {
  return `${base} ${variants[variant]}`;
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
};

export function Button({
  variant = "primary",
  type = "button",
  className = "",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`${buttonVariants(variant)} ${className}`}
      {...props}
    />
  );
}

type ButtonLinkProps = ComponentProps<typeof Link> & {
  variant?: ButtonVariant;
};

export function ButtonLink({
  variant = "primary",
  className = "",
  ...props
}: ButtonLinkProps) {
  return (
    <Link className={`${buttonVariants(variant)} ${className}`} {...props} />
  );
}
