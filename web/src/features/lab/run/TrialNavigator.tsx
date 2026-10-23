import { ChevronLeft, ChevronRight } from "lucide-react";

import { IconButton } from "../../../components/IconButton";
import { Term } from "../../../components/Term";

/** "Recorded run 2 of 3" with previous and next buttons that replay another trial. */
export function TrialNavigator({
  trial,
  available,
  disabled,
  onChange,
}: {
  trial: number;
  available: number;
  disabled: boolean;
  onChange: (trial: number) => void;
}) {
  const total = Math.max(available, trial);
  return (
    <div className="flex items-center justify-between gap-3 text-small text-ink-2">
      <p>
        <Term id="recordedRun">Recorded run</Term> {trial} of {total}
      </p>
      {total > 1 && (
        <div className="flex gap-2">
          <IconButton
            icon={ChevronLeft}
            label="Previous recorded run"
            disabled={disabled || trial <= 1}
            onClick={() => onChange(trial - 1)}
          />
          <IconButton
            icon={ChevronRight}
            label="Next recorded run"
            disabled={disabled || trial >= total}
            onClick={() => onChange(trial + 1)}
          />
        </div>
      )}
    </div>
  );
}
