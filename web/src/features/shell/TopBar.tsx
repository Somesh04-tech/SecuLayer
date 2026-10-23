import { clsx } from "clsx";
import { Link, NavLink } from "react-router";

import { Container } from "../../components/Page";
import { ModeIndicator } from "./ModeIndicator";
import { TextSizeToggle } from "./TextSizeToggle";

const NAV = [
  { to: "/lab", label: "Demo" },
  { to: "/how", label: "How it works" },
  { to: "/results", label: "Results" },
  { to: "/limits", label: "Limits" },
  { to: "/sandbox", label: "Try your own" },
] as const;

export function TopBar() {
  return (
    <header className="border-b border-border bg-page">
      <Container className="flex h-16 items-center gap-10">
        <Link to="/" className="text-h3 font-bold text-ink">
          SecuLayer
        </Link>
        <nav aria-label="Main" className="flex h-full items-stretch gap-6">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                clsx(
                  "relative inline-flex items-center text-small font-semibold whitespace-nowrap",
                  "transition-colors duration-(--duration-hover) ease-standard",
                  "after:absolute after:inset-x-0 after:-bottom-px after:h-0.5",
                  isActive
                    ? "text-accent after:bg-accent"
                    : "text-ink-2 after:bg-transparent hover:text-ink",
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-3">
          <TextSizeToggle />
          <ModeIndicator />
        </div>
      </Container>
    </header>
  );
}
