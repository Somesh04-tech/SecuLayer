import { ChevronDown, RotateCcw } from "lucide-react";
import { useId, type ReactNode } from "react";

import { LAYERS, LAYER_LABELS, type LayerName } from "../../../api/types";
import { Button } from "../../../components/Button";
import { Popover } from "../../../components/Popover";
import { Switch } from "../../../components/Switch";
import { Term } from "../../../components/Term";

export type LayerSettings = Record<LayerName, boolean>;

export const ALL_ON: LayerSettings = {
  hidden_text: true,
  screening: true,
  hardening: true,
  tool_guard: true,
  output_guard: true,
};

const DESCRIPTIONS: Record<LayerName, ReactNode> = {
  hidden_text: "Removes text a person can't see before the model reads it.",
  screening: (
    <>
      Checks each input with rules, a <Term id="classifier">classifier</Term> and an{" "}
      <Term id="llmJudge">AI judge</Term>.
    </>
  ),
  hardening: "Marks outside content and tells the model it can't give orders.",
  tool_guard: "Checks every action before it runs, and asks when in doubt.",
  output_guard: (
    <>
      Checks the reply for secrets, the <Term id="canaryToken">canary</Term> and risky links before
      it's shown.
    </>
  ),
};

export function layersOn(layers: LayerSettings): number {
  return LAYERS.filter((l) => layers[l]).length;
}

export function layerSummary(layers: LayerSettings): string {
  const on = layersOn(layers);
  return on === LAYERS.length ? `Layers: all ${on} on` : `Layers: ${on} of ${LAYERS.length} on`;
}

/** The Layers menu (§4.5): five switches, each with a one-line description, and a reset. */
export function LayerMenu({
  layers,
  onChange,
  disabled = false,
}: {
  layers: LayerSettings;
  onChange: (layers: LayerSettings) => void;
  disabled?: boolean;
}) {
  const id = useId();
  const allOn = layersOn(layers) === LAYERS.length;
  return (
    <Popover
      label="SecuLayer's layers"
      trigger={
        <Button
          variant="secondary"
          size="small"
          trailingIcon={ChevronDown}
          disabled={disabled}
          data-testid="layer-menu"
        >
          {layerSummary(layers)}
        </Button>
      }
    >
      <p className="text-small font-semibold text-ink">SecuLayer's layers</p>
      <p className="mt-1 text-small text-ink-2">
        Switch layers off, then run again to see what the others catch.
      </p>
      <ul className="mt-4 space-y-4">
        {LAYERS.map((layer) => (
          <li key={layer}>
            <Switch
              label={LAYER_LABELS[layer]}
              checked={layers[layer]}
              describedBy={`${id}-${layer}`}
              onCheckedChange={(checked) => onChange({ ...layers, [layer]: checked })}
            />
            <p id={`${id}-${layer}`} className="mt-1 pl-12 text-caption text-ink-3">
              {DESCRIPTIONS[layer]}
            </p>
          </li>
        ))}
      </ul>
      <Button
        className="mt-5"
        variant="ghost"
        size="small"
        icon={RotateCcw}
        disabled={allOn}
        onClick={() => onChange(ALL_ON)}
      >
        Reset to all on
      </Button>
    </Popover>
  );
}
