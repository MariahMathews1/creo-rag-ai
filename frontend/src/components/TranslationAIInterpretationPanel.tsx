import type { MachineProfile } from "../types";
import "./translation-ai.css";

/**
 * Compatibility shell for previous routes/imports.
 *
 * Deliberately contains no provider calls and no CL/NCL input. The backend also
 * rejects the retired invocation, so restoring an old route cannot bypass the
 * current governance boundary.
 */
export function TranslationAIInterpretationPanel(_props: {
  machines: MachineProfile[];
  initialMachineId?: number;
  initialRevisionId?: number;
  initialCl?: string;
  compact?: boolean;
}) {
  return <section className="translation-ai-panel panel deprecated-ai-experiment">
    <header><div><span className="eyebrow">Deprecated / Previous R&amp;D Experiment</span><h2>Legacy CL/NCL AI workflow disabled</h2></div></header>
    <p>This compatibility view cannot invoke an AI provider. Historical examples remain available for local deterministic analysis only.</p>
    <strong>AI_CL_NCL_TRANSMISSION_PROHIBITED</strong>
  </section>;
}
