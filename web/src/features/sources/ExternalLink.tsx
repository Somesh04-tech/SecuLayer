import { ExternalLink as ExternalIcon } from "lucide-react";
import type { ReactNode } from "react";

import { domainOf } from "../../content/sources";

/** A citation link: opens the source in a new tab and shows its domain. */
export function ExternalLink({
  href,
  children,
  showDomain = true,
}: {
  href: string;
  children: ReactNode;
  showDomain?: boolean;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="font-semibold text-accent underline-offset-4 transition-colors duration-(--duration-hover) ease-standard hover:text-accent-hover hover:underline"
    >
      {children}
      {showDomain && <span className="font-normal text-ink-3"> ({domainOf(href)})</span>}
      <ExternalIcon
        size={14}
        strokeWidth={1.75}
        aria-hidden="true"
        className="ml-1 inline align-[-2px]"
      />
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  );
}
