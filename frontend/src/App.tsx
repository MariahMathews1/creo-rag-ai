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
import { LegacyPostBuilderWorkspacePage } from "./pages/PostBuilderWorkspacePage";
import { PostRecordWorkspacePage } from "./pages/PostRecordWorkspacePage";
import { TranslationExamplesPage } from "./pages/TranslationExamplesPage";
import { TranslationDetailPage } from "./pages/TranslationDetailPage";
import { ResearchGate, ResearchToolsPage } from "./pages/ResearchToolsPage";
import { MachineDetailPage } from "./pages/MachineDetailPage";
import { ManualMachineInformationPage } from "./pages/ManualMachineInformationPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="machines" element={<MachineProfilesPage />} />
          <Route path="machines/:machineId/:view?" element={<MachineDetailPage />} />
          <Route path="machines/:machineId/machine-information/manual" element={<ManualMachineInformationPage />} />
          <Route path="analysis/new" element={<ResearchGate><NewAnalysisPage /></ResearchGate>} />
          <Route path="g-code-review" element={<ResearchGate><NewAnalysisPage /></ResearchGate>} />
          <Route path="analysis/:projectId" element={<ResearchGate><AnalysisResultsPage /></ResearchGate>} />
          <Route path="analyses/:analysisId/traceability" element={<ResearchGate><TraceabilityPage /></ResearchGate>} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="documents/:documentId" element={<DocumentViewerPage />} />
          <Route path="manual-assistant" element={<ManualAssistantPage />} />
          <Route path="machine-assistant" element={<ManualAssistantPage />} />
          <Route path="gpost" element={<GPostGeneratorPage />} />
          <Route path="gpost/:draftId/advanced/legacy-preview" element={<GPostWorkspacePage />} />
          <Route path="gpost/:draftId/advanced/legacy-ai-workspace/*" element={<LegacyPostBuilderWorkspacePage />} />
          <Route path="gpost/:draftId/*" element={<PostRecordWorkspacePage />} />
          <Route path="translations" element={<ResearchGate><TranslationExamplesPage /></ResearchGate>} />
          <Route path="translations/patterns" element={<ResearchGate><TranslationExamplesPage /></ResearchGate>} />
          <Route path="translations/ai-experiment" element={<ResearchGate><TranslationExamplesPage /></ResearchGate>} />
          <Route path="translations/technical" element={<ResearchGate><TranslationExamplesPage /></ResearchGate>} />
          <Route path="translations/:exampleId" element={<ResearchGate><TranslationDetailPage /></ResearchGate>} />
          <Route path="research-tools" element={<ResearchToolsPage />} />
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
