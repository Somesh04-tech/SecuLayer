import { Page } from "../components/Page";
import { SOURCES_CHECKED_ON } from "../content/sources";
import { Credits, GeneralSources, IncidentTable } from "../features/sources/SourceSections";

export function SourcesPage() {
  return (
    <Page
      title="Sources"
      lead="Every incident, paper and framework this app cites, with links and dates, plus license credits."
    >
      <p className="text-small text-ink-3">All sources were checked on {SOURCES_CHECKED_ON}.</p>
      <GeneralSources />
      <IncidentTable />
      <Credits />
    </Page>
  );
}
