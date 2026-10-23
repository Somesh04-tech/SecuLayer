import { Link } from "react-router";

import { Container } from "../../components/Page";

export function Footer() {
  return (
    <footer className="border-t border-border">
      <Container className="flex items-center justify-between gap-6 py-6 text-small text-ink-3">
        <p>Everything here is a sandbox with fake data. Nothing leaves this computer.</p>
        <Link
          to="/sources"
          className="font-semibold text-accent underline-offset-4 transition-colors duration-(--duration-hover) ease-standard hover:text-accent-hover hover:underline"
        >
          Sources
        </Link>
      </Container>
    </footer>
  );
}
