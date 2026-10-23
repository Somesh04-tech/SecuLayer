import { RotateCw, Unplug } from "lucide-react";
import { useEffect } from "react";
import { Outlet, useLocation } from "react-router";

import { Button } from "../../components/Button";
import { Code } from "../../components/Code";
import { ErrorState } from "../../components/EmptyState";
import { Container } from "../../components/Page";
import { TooltipProvider } from "../../components/Tooltip";
import { Footer } from "./Footer";
import { MetaProvider, useMeta } from "./meta";
import { TopBar } from "./TopBar";

function ServerUnreachable() {
  const meta = useMeta();
  return (
    <Container className="py-12">
      <ErrorState
        icon={Unplug}
        title="Can't reach the SecuLayer server."
        help={
          <>
            Is <Code>./run.sh</Code> still running?
          </>
        }
        action={
          <Button variant="secondary" icon={RotateCw} onClick={meta.retry}>
            Try again
          </Button>
        }
      />
    </Container>
  );
}

function Main() {
  const meta = useMeta();
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return (
    <main id="main" tabIndex={-1} className="flex-1">
      {meta.status === "error" ? <ServerUnreachable /> : <Outlet />}
    </main>
  );
}

/** The frame on every screen: top bar, page, footer. */
export function AppShell() {
  return (
    <MetaProvider>
      <TooltipProvider delayDuration={300}>
        <div className="flex min-h-screen flex-col bg-page">
          <a
            href="#main"
            className="sr-only rounded-control bg-page px-4 py-2 text-small font-semibold text-accent focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:border focus:border-border-control"
          >
            Skip to main content
          </a>
          <TopBar />
          <Main />
          <Footer />
        </div>
      </TooltipProvider>
    </MetaProvider>
  );
}
