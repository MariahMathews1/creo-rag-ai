import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AnalysisResultsPage } from "./pages/AnalysisResultsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { MachineProfilesPage } from "./pages/MachineProfilesPage";
import { NewAnalysisPage } from "./pages/NewAnalysisPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { DocumentViewerPage } from "./pages/DocumentViewerPage";
import { ManualAssistantPage } from "./pages/ManualAssistantPage";
import { TraceabilityPage } from "./pages/TraceabilityPage";
import { ProfileExtractionSetupPage } from "./pages/ProfileExtractionSetupPage";
import { ProfileExtractionReviewPage } from "./pages/ProfileExtractionReviewPage";
import { ProfileRevisionsPage } from "./pages/ProfileRevisionsPage";
import { ReferenceProgramsPage } from "./pages/ReferenceProgramsPage";
import { StandardExtractionReviewPage } from "./pages/StandardExtractionReviewPage";
import { ApprovedProgramComparisonPage } from "./pages/ApprovedProgramComparisonPage";
import { GPostGeneratorPage } from "./pages/GPostGeneratorPage";
import { GPostWorkspacePage } from "./pages/GPostWorkspacePage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="machines" element={<MachineProfilesPage />} />
          <Route path="analysis/new" element={<NewAnalysisPage />} />
          <Route path="analysis/:projectId" element={<AnalysisResultsPage />} />
          <Route path="analyses/:analysisId/traceability" element={<TraceabilityPage />} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="documents/:documentId" element={<DocumentViewerPage />} />
          <Route path="manual-assistant" element={<ManualAssistantPage />} />
          <Route path="gpost" element={<GPostGeneratorPage />} />
          <Route path="gpost/:draftId" element={<GPostWorkspacePage />} />
          <Route path="machines/:machineId/profile-extraction/new" element={<ProfileExtractionSetupPage />} />
          <Route path="machines/:machineId/profile-extraction/:runId" element={<ProfileExtractionReviewPage />} />
          <Route path="machines/:machineId/revisions" element={<ProfileRevisionsPage />} />
          <Route path="machines/:machineId/reference-programs" element={<ReferenceProgramsPage />} />
          <Route path="machines/:machineId/standards/extraction/:runId" element={<StandardExtractionReviewPage />} />
          <Route path="analyses/:analysisId/approved-program-comparison/:comparisonId" element={<ApprovedProgramComparisonPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
