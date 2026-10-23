import { ALargeSmall } from "lucide-react";
import { useEffect, useState } from "react";

import { IconButton } from "../../components/IconButton";
import { applyTextSize, readTextSize, writeTextSize, type TextSize } from "./textSize";

/** Switches large-text mode, which scales every size by 1.125 for the back of the room. */
export function TextSizeToggle() {
  const [size, setSize] = useState<TextSize>(readTextSize);
  const large = size === "large";

  useEffect(() => {
    applyTextSize(size);
  }, [size]);

  return (
    <IconButton
      icon={ALargeSmall}
      label="Large text"
      tooltip={large ? "Large text is on" : "Large text is off"}
      aria-pressed={large}
      onClick={() => {
        const next: TextSize = large ? "normal" : "large";
        writeTextSize(next);
        setSize(next);
      }}
    />
  );
}
