import { clsx } from "clsx";
import { ChevronRight } from "lucide-react";
import { Collapsible } from "radix-ui";
import { useState, type ReactNode } from "react";

/**
 * A section that expands in place (§4.5): "How this app is built", "About this attack".
 * The chevron rotates 90° when open.
 */
export function Disclosure({
  title,
  children,
  defaultOpen = false,
  className,
}: {
  title: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  className?: string;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Collapsible.Root open={open} onOpenChange={setOpen} className={className}>
      <Collapsible.Trigger className="inline-flex items-center gap-1.5 rounded-control text-small font-semibold text-ink transition-colors duration-(--duration-hover) ease-standard hover:text-accent">
        <ChevronRight
          size={16}
          strokeWidth={1.75}
          aria-hidden="true"
          className={clsx(
            "transition-transform duration-(--duration-expand) ease-standard",
            open && "rotate-90",
          )}
        />
        {title}
      </Collapsible.Trigger>
      <Collapsible.Content className="mt-3 pl-5.5">{children}</Collapsible.Content>
    </Collapsible.Root>
  );
}
