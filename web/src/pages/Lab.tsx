import { ChevronLeft, FlaskConical } from "lucide-react";
import { Link, useParams } from "react-router";

import { ButtonLink } from "../components/Button";
import { Code } from "../components/Code";
import { EmptyState } from "../components/EmptyState";
import { Page } from "../components/Page";

export function LabPage() {
  const { scenarioId } = useParams();

  return (
    <Page
      title="Attack Lab"
      lead="Run an attack against a toy app without SecuLayer, then with it, and see exactly what changed."
      breadcrumb={
        <nav aria-label="Breadcrumb" className="mb-3">
          <Link
            to="/"
            className="inline-flex items-center gap-1 text-small font-semibold text-accent hover:text-accent-hover hover:underline underline-offset-4"
          >
            <ChevronLeft size={16} strokeWidth={1.75} aria-hidden="true" />
            All scenarios
          </Link>
        </nav>
      }
    >
      <EmptyState
        icon={FlaskConical}
        title="No scenarios to show yet"
        help={
          scenarioId ? (
            <>
              There's no scenario called <Code>{scenarioId}</Code> in this build yet. Its attacks
              and normal-use cases appear here once the scenario data is added.
            </>
          ) : (
            "The attacks and normal-use cases appear here once the scenario data is added to this build."
          )
        }
        action={
          <ButtonLink to="/" variant="secondary">
            Back to the home page
          </ButtonLink>
        }
      />
    </Page>
  );
}
