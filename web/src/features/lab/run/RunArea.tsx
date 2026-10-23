import { useCallback, useEffect, useId, useRef, useState, type RefObject } from "react";

import type { CaseDetail, ScenarioDetail } from "../../../api/types";
import { useMeta } from "../../shell/meta";
import { useRun } from "../useRun";
import { ALL_ON, type LayerSettings } from "./LayerMenu";
import { PromptAnatomy } from "./PromptAnatomy";
import { RunColumn, type RegisterStarter, type Side, type Starters } from "./RunColumn";

/**
 * Which model both columns run (§9 M5). In replay mode a model with no recordings is
 * disabled, because there would be nothing to replay.
 */
function ModelSelect({
  value,
  onChange,
  disabled,
}: {
  value: string | undefined;
  onChange: (model: string) => void;
  disabled: boolean;
}) {
  const meta = useMeta();
  const id = useId();
  if (meta.status !== "ok") return null;
  const { target, compare } = meta.data.models;
  const replay = meta.data.mode === "replay";
  const recorded = new Set(meta.data.recordings.models);
  const options = [
    { model: target, label: `${target} (the demo's model)` },
    { model: compare, label: `${compare} (a stronger model)` },
  ];
  return (
    <div className="flex flex-wrap items-center gap-2 text-small">
      <label htmlFor={id} className="font-semibold text-ink">
        Model
      </label>
      <select
        id={id}
        value={value ?? target}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="h-8 rounded-control border border-border-control bg-page px-2 text-small text-ink disabled:opacity-50"
      >
        {options.map((o) => {
          const missing = replay && !recorded.has(o.model);
          return (
            <option key={o.model} value={o.model} disabled={missing}>
              {o.label}
              {missing ? " · not recorded" : ""}
            </option>
          );
        })}
      </select>
    </div>
  );
}

/**
 * The two run columns, without and with SecuLayer, and what the model received (§3.3).
 * Mount it with `key={caseId}` so a new case starts from a clean slate.
 */
export function RunArea({
  scenario,
  caseDetail,
  runRef,
}: {
  scenario: ScenarioDetail;
  caseDetail: CaseDetail;
  /** Set to a function that starts a column's run, for the presenter shortcuts. */
  runRef?: RefObject<((side: Side) => void) | null>;
}) {
  const without = useRun();
  const withSecuLayer = useRun();
  const [ranWithout, setRanWithout] = useState(false);
  const [last, setLast] = useState<Side | null>(null);
  const [layers, setLayers] = useState<LayerSettings>(ALL_ON);
  const [model, setModel] = useState<string | undefined>(undefined);
  const starters = useRef<Starters>({});
  const register = useCallback<RegisterStarter>((side, start) => {
    if (start) starters.current[side] = start;
    else delete starters.current[side];
  }, []);
  const busy = without.state.status === "running" || withSecuLayer.state.status === "running";

  useEffect(() => {
    if (!runRef) return;
    runRef.current = (side) => starters.current[side]?.();
    return () => {
      runRef.current = null;
    };
  }, [runRef]);

  return (
    <div className="space-y-6">
      <ModelSelect value={model} onChange={setModel} disabled={busy} />
      <div className="grid gap-6 lg:grid-cols-2">
        <RunColumn
          side="without"
          run={without}
          scenario={scenario}
          caseDetail={caseDetail}
          primary={!ranWithout}
          model={model}
          register={register}
          onRun={() => {
            setRanWithout(true);
            setLast("without");
          }}
        />
        <RunColumn
          side="with"
          run={withSecuLayer}
          scenario={scenario}
          caseDetail={caseDetail}
          primary={ranWithout}
          model={model}
          register={register}
          layers={layers}
          onLayersChange={setLayers}
          onRun={() => setLast("with")}
        />
      </div>
      <PromptAnatomy without={without.state} withSecuLayer={withSecuLayer.state} last={last} />
    </div>
  );
}
