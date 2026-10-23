import { MapPinOff } from "lucide-react";
import { useLocation } from "react-router";

import { ButtonLink } from "../components/Button";
import { Code } from "../components/Code";
import { EmptyState } from "../components/EmptyState";
import { Page } from "../components/Page";

export function NotFoundPage() {
  const { pathname } = useLocation();
  return (
    <Page title="Page not found">
      <EmptyState
        icon={MapPinOff}
        title={
          <>
            There's no page at <Code>{pathname}</Code>.
          </>
        }
        help="The address may be mistyped, or the page may have moved."
        action={
          <ButtonLink to="/" variant="primary">
            Go to the home page
          </ButtonLink>
        }
      />
    </Page>
  );
}
