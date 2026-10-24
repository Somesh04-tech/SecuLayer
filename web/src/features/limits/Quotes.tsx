import { QUOTES, sourceById } from "../../content/sources";
import { ExternalLink } from "../sources/ExternalLink";

export function Quotes() {
  const ncsc = sourceById("ncsc");
  return (
    <section aria-labelledby="limits-quotes" className="mt-14">
      <h2 id="limits-quotes" className="text-h2 text-ink">
        What the people building these systems say
      </h2>
      <div className="mt-6 max-w-prose space-y-8">
        {Object.values(QUOTES).map((quote) => {
          const source = sourceById(quote.sourceId);
          return (
            <figure key={quote.sourceId} className="border-l-3 border-border-strong pl-5">
              <blockquote className="text-lead text-ink">
                <p>“{quote.text}”</p>
              </blockquote>
              <figcaption className="mt-2 text-small text-ink-2">
                {quote.by},{" "}
                <ExternalLink href={source.links[0]?.url ?? ""}>{source.title}</ExternalLink>
              </figcaption>
            </figure>
          );
        })}
        <p className="text-body text-ink-2">
          The UK's National Cyber Security Centre makes the same point in{" "}
          <ExternalLink href={ncsc.links[0]?.url ?? ""}>“{ncsc.title}”</ExternalLink> ({ncsc.date}):
          unlike SQL injection, there is no clean separation between instructions and data to
          restore.
        </p>
      </div>
    </section>
  );
}
