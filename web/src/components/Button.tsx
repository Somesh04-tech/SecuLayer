import { clsx } from "clsx";
import type { ComponentPropsWithRef, ReactNode } from "react";
import { Link, type LinkProps } from "react-router";
import type { LucideIcon } from "lucide-react";

export type ButtonVariant = "primary" | "secondary" | "ghost";
export type ButtonSize = "default" | "small";

const base =
  "inline-flex shrink-0 items-center justify-center gap-2 rounded-control text-small font-semibold whitespace-nowrap " +
  "transition-colors duration-(--duration-hover) ease-standard " +
  "disabled:cursor-not-allowed disabled:opacity-50";

const variants: Record<ButtonVariant, string> = {
  primary: "bg-accent text-page hover:bg-accent-hover active:bg-accent-hover",
  secondary: "border border-border-control bg-page text-ink hover:border-ink-2 hover:text-ink",
  ghost: "text-accent hover:text-accent-hover hover:underline underline-offset-4",
};

const sizes: Record<ButtonSize, Record<ButtonVariant, string>> = {
  default: { primary: "h-10 px-4", secondary: "h-10 px-4", ghost: "h-10 px-1" },
  small: { primary: "h-8 px-3", secondary: "h-8 px-3", ghost: "h-8 px-1" },
};

export function buttonClasses({
  variant = "secondary",
  size = "default",
  className,
}: {
  variant?: ButtonVariant | undefined;
  size?: ButtonSize | undefined;
  className?: string | undefined;
}): string {
  return clsx(base, sizes[size][variant], variants[variant], className);
}

interface CommonProps {
  variant?: ButtonVariant | undefined;
  size?: ButtonSize | undefined;
  icon?: LucideIcon | undefined;
  /** Icon after the label instead of before it, e.g. a "go" chevron on a text link. */
  trailingIcon?: LucideIcon | undefined;
  children: ReactNode;
}

function Content({ icon: Icon, trailingIcon: Trailing, children }: CommonProps) {
  return (
    <>
      {Icon && <Icon size={16} strokeWidth={1.75} aria-hidden="true" />}
      {children}
      {Trailing && <Trailing size={16} strokeWidth={1.75} aria-hidden="true" />}
    </>
  );
}

export type ButtonProps = CommonProps & Omit<ComponentPropsWithRef<"button">, "children">;

export function Button({
  variant,
  size,
  icon,
  trailingIcon,
  className,
  children,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button type={type} className={buttonClasses({ variant, size, className })} {...props}>
      <Content icon={icon} trailingIcon={trailingIcon}>
        {children}
      </Content>
    </button>
  );
}

export type ButtonLinkProps = CommonProps & Omit<LinkProps, "children">;

/** A router link that looks like a button. */
export function ButtonLink({
  variant,
  size,
  icon,
  trailingIcon,
  className,
  children,
  ...props
}: ButtonLinkProps) {
  return (
    <Link className={buttonClasses({ variant, size, className })} {...props}>
      <Content icon={icon} trailingIcon={trailingIcon}>
        {children}
      </Content>
    </Link>
  );
}
