import type { Source, SourceGroup } from "../../content/sources";
import { ATLAS_TECHNIQUES, SOURCES } from "../../content/sources";
import { ExternalLink } from "./ExternalLink";

const SECTIONS: { group: Exclude<SourceGroup, "incident" | "credit">; title: string }[] = [
  { group: "framework", title: "Frameworks" },
  { group: "guidance", title: "Vendor and government guidance" },
  { group: "research", title: "Research and essays" },
];

function SourceItem({ source }: { source: Source }) {
  const single = source.links.length === 1 ? source.links[0] : undefined;
  return (
    <li className="py-4">
      <p className="text-body text-ink">
        {single ? (
          <ExternalLink href={single.url}>{source.title}</ExternalLink>
        ) : (
          <span className="font-semibold">{source.title}</span>
        )}
      </p>
      <p className="text-small text-ink-3">
        {source.by}
        {source.date && <span className="tabular-nums"> · {source.date}</span>}
      </p>
      {source.note && <p className="mt-1 max-w-prose text-small text-ink-2">{source.note}</p>}
      {!single && (
        <ul className="mt-2 space-y-1 text-small">
          {source.links.map((link) => (
            <li key={link.url}>
              <ExternalLink href={link.url}>{link.label ?? "Main page"}</ExternalLink>
            </li>
          ))}
        </ul>
      )}
      {source.id === "mitre-atlas" && (
        <ul className="mt-2 grid max-w-3xl grid-cols-2 gap-x-6 text-small text-ink-2">
          {ATLAS_TECHNIQUES.map((t) => (
            <li key={t.id}>
              <span className="font-mono text-mono">{t.id}</span> {t.name}
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

export function SourceList({ group, title }: { group: SourceGroup; title: string }) {
  const sources = SOURCES.filter((s) => s.group === group);
  const id = `sources-${group}`;
  return (
    <section aria-labelledby={id} className="mt-12">
      <h2 id={id} className="text-h2 text-ink">
        {title}
      </h2>
      <ul className="mt-2 divide-y divide-border border-y border-border">
        {sources.map((source) => (
          <SourceItem key={source.id} source={source} />
        ))}
      </ul>
    </section>
  );
}

export function GeneralSources() {
  return (
    <>
      {SECTIONS.map((section) => (
        <SourceList key={section.group} group={section.group} title={section.title} />
      ))}
    </>
  );
}

export function IncidentTable() {
  const incidents = SOURCES.filter((s) => s.group === "incident");
  return (
    <section aria-labelledby="sources-incidents" className="mt-12">
      <h2 id="sources-incidents" className="text-h2 text-ink">
        Incidents
      </h2>
      <p className="mt-2 max-w-prose text-body text-ink-2">
        Real prompt-injection incidents the attacks in this demo are modelled on, oldest first.
      </p>
      <table className="mt-4 w-full border-collapse text-left text-small">
        <thead>
          <tr className="border-b border-border-strong bg-surface-muted text-ink-2">
            <th scope="col" className="w-28 px-3 py-2 font-semibold">
              Date
            </th>
            <th scope="col" className="px-3 py-2 font-semibold">
              Incident
            </th>
            <th scope="col" className="px-3 py-2 font-semibold">
              Sources
            </th>
          </tr>
        </thead>
        <tbody>
          {incidents.map((incident) => (
            <tr key={incident.id} className="border-b border-border align-top">
              <td className="px-3 py-3 tabular-nums text-ink-2">{incident.date}</td>
              <th scope="row" className="px-3 py-3 font-semibold text-ink">
                {incident.title}
                {incident.note && (
                  <span className="block font-normal text-ink-3">{incident.note}</span>
                )}
              </th>
              <td className="px-3 py-3">
                <ul className="space-y-1">
                  {incident.links.map((link, index) => (
                    <li key={link.url}>
                      <ExternalLink href={link.url}>
                        {link.label ?? (index === 0 ? incident.by : "Link")}
                      </ExternalLink>
                    </li>
                  ))}
                </ul>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export function Credits() {
  const credit = SOURCES.filter((s) => s.group === "credit");
  return (
    <section aria-labelledby="sources-credits" className="mt-12">
      <h2 id="sources-credits" className="text-h2 text-ink">
        Credits
      </h2>
      {credit.map((source) => (
        <div key={source.id} className="mt-4 max-w-prose">
          <p className="text-h3 text-ink">Built with Llama</p>
          <p className="mt-1 text-body text-ink-2">
            The screening layer's classifier is Meta's {source.title}, licensed under the Llama 4
            Community License.
          </p>
          <ul className="mt-2 space-y-1 text-small">
            {source.links.map((link) => (
              <li key={link.url}>
                <ExternalLink href={link.url}>{link.label ?? source.title}</ExternalLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
      <p className="mt-6 max-w-prose text-small text-ink-2">
        Fonts: Atkinson Hyperlegible Next and Mono by the Braille Institute, under the SIL Open Font
        License.
      </p>
    </section>
  );
}
