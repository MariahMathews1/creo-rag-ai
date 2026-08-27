import type { ReactNode } from "react";
import { Link, Navigate } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";

export function ResearchGate({ children }: { children: ReactNode }) {
  return import.meta.env.VITE_ENABLE_RESEARCH_TOOLS === "true" ? children : <Navigate to="/" replace />;
}

export function ResearchToolsPage() {
  return <ResearchGate><section className="page"><PageHeader eyebrow="Developer only" title="Research Tools" description="Legacy R&D tools retained outside the V1 NC programmer workflow." />
    <section className="panel technical-links"><Link to="/translations">Historical Post Examples / Translation Explorer</Link><Link to="/g-code-review">G-code Review</Link><Link to="/translations/technical">Alignment and Dataset Technical Details</Link><Link to="/translations/ai-experiment">Legacy AI Experiments</Link></section>
  </section></ResearchGate>;
}
