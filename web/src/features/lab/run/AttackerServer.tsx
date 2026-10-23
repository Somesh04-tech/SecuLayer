import { Server } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

import type { AttackerEvent } from "../../../api/types";
import { Term } from "../../../components/Term";

const CHANNEL: Record<AttackerEvent["channel"], string> = {
  email: "Email received",
  image: "Image request received",
  link: "Link prepared",
  chat: "Chat reply received",
};

/** What the attacker's (simulated) server received. Shown only when it has entries. */
export function AttackerServer({
  events,
  userName,
}: {
  events: AttackerEvent[];
  userName: string;
}) {
  const reduced = useReducedMotion();
  return (
    <section
      data-testid="attacker-server"
      aria-label="Attacker's server (simulated)"
      className="rounded-card border border-danger-border px-4 py-3"
    >
      <h3 className="flex items-center gap-2 text-small font-semibold text-ink">
        <Server size={16} strokeWidth={1.75} aria-hidden="true" className="text-danger-solid" />
        Attacker's server (simulated)
      </h3>
      <p className="mt-1 text-caption text-ink-3">
        What reached the attacker: <Term id="exfiltration">exfiltration</Term>.
      </p>
      {events.length === 0 ? (
        <p className="mt-2 text-small text-ink-3">Nothing received yet.</p>
      ) : (
        <ul className="mt-2 space-y-3">
          <AnimatePresence initial={!reduced}>
            {events.map((event, index) => (
              <motion.li
                key={`${event.channel}-${event.destination}-${index}`}
                initial={reduced ? false : { opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: reduced ? 0 : 0.24, ease: [0.2, 0.7, 0.2, 1] }}
                className="text-small"
              >
                <p className="text-ink-2">
                  {CHANNEL[event.channel]} ·{" "}
                  <span className="font-mono text-mono break-all text-ink">
                    {event.destination}
                  </span>{" "}
                  ·{" "}
                  {event.zero_click
                    ? event.channel === "chat"
                      ? "shown to the attacker"
                      : "zero-click"
                    : `if ${userName} clicks`}
                </p>
                <p className="mt-1 rounded-chip bg-danger-bg px-2 py-1 break-words text-danger-ink">
                  {event.data}
                </p>
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}
    </section>
  );
}
