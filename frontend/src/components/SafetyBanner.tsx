export const SAFETY_MESSAGE =
  "Advisory tool only. This application does not certify CNC programs for production. All output must be reviewed, simulated, and approved by a qualified CNC programmer before use on any machine.";

export function SafetyBanner({
  title = "Production-use warning",
  message = SAFETY_MESSAGE,
}: { title?: string; message?: string } = {}) {
  return (
    <aside className="safety-banner" role="alert">
      <span className="safety-icon" aria-hidden="true">!</span>
      <div>
        <strong>{title}</strong>
        <p>{message}</p>
      </div>
    </aside>
  );
}
