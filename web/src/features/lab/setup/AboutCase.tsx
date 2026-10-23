import { ExternalLink } from "lucide-react";
import type { ReactNode } from "react";

import type { CaseDetail } from "../../../api/types";
import { Chip } from "../../../components/Chip";
import { Disclosure } from "../../../components/Disclosure";

function domainOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-small font-semibold text-ink">{label}</dt>
      <dd className="mt-0.5 text-body text-ink-2">{children}</dd>
    </div>
  );
}

/** "About this attack" (or, for normal use, why the case is in the set). */
export function AboutCase({ caseDetail }: { caseDetail: CaseDetail }) {
  if (caseDetail.kind === "normal") {
    return (
      <Disclosure title="About this case">
        <dl className="max-w-prose space-y-3">
          <Row label="Why it's here">{caseDetail.why_here}</Row>
        </dl>
      </Disclosure>
    );
  }
  const source = caseDetail.real_world;
  return (
    <Disclosure title="About this attack">
      <dl className="max-w-prose space-y-3">
        <Row label="The attacker's goal">{caseDetail.goal}</Row>
        <Row label="In plain language">{caseDetail.explanation}</Row>
        {caseDetail.why_it_works && <Row label="Why it works">{caseDetail.why_it_works}</Row>}
        {caseDetail.what_stops_it && (
          <Row label="What SecuLayer does">{caseDetail.what_stops_it}</Row>
        )}
        {caseDetail.expected && (
          <Row label="Expected, before measurement">{caseDetail.expected}</Row>
        )}
        {source && source.url && (
          <Row label="It happened for real">
            <a
              href={source.url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-baseline gap-1 font-semibold text-accent underline-offset-4 hover:text-accent-hover hover:underline"
            >
              {source.title}
              <ExternalLink
                size={14}
                strokeWidth={1.75}
                aria-hidden="true"
                className="self-center"
              />
            </a>{" "}
            <span className="text-small text-ink-3">
              ({domainOf(source.url)}, {source.date})
            </span>
          </Row>
        )}
        {caseDetail.frameworks.length > 0 && (
          <Row label="Framework tags">
            <span className="mt-1 flex flex-wrap gap-1.5">
              {caseDetail.frameworks.map((tag) => (
                <Chip key={tag}>{tag}</Chip>
              ))}
            </span>
          </Row>
        )}
      </dl>
    </Disclosure>
  );
}
