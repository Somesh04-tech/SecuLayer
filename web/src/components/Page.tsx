import { useEffect, type ReactNode } from "react";

/** The content column: at most 1320 px wide, 24 px gutters below 1280 px and 32 px above. */
export function Container({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={`mx-auto w-full max-w-content px-6 xl:px-8 ${className}`}>{children}</div>;
}

/** A standard page: title, optional lead paragraph, then the page body. */
export function Page({
  title,
  lead,
  breadcrumb,
  children,
}: {
  title: string;
  lead?: ReactNode;
  breadcrumb?: ReactNode;
  children?: ReactNode;
}) {
  useEffect(() => {
    document.title = `${title} · SecuLayer`;
  }, [title]);

  return (
    <Container className="py-12">
      {breadcrumb}
      <h1 className="text-h1 text-ink">{title}</h1>
      {lead && <p className="mt-3 max-w-prose text-lead text-ink-2">{lead}</p>}
      {children && <div className="mt-10">{children}</div>}
    </Container>
  );
}
