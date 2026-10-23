import { BrowserRouter, Route, Routes } from "react-router";

import { AppShell } from "./features/shell/AppShell";
import { HomePage } from "./pages/Home";
import { HowItWorksPage } from "./pages/HowItWorks";
import { LabPage } from "./pages/Lab";
import { LimitsPage } from "./pages/Limits";
import { NotFoundPage } from "./pages/NotFound";
import { ResultsPage } from "./pages/Results";
import { SandboxPage } from "./pages/Sandbox";
import { SourcesPage } from "./pages/Sources";

/** Every screen in docs/PLAN.md §3.2. */
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<HomePage />} />
        <Route path="lab/:scenarioId?" element={<LabPage />} />
        <Route path="how" element={<HowItWorksPage />} />
        <Route path="results" element={<ResultsPage />} />
        <Route path="limits" element={<LimitsPage />} />
        <Route path="sandbox" element={<SandboxPage />} />
        <Route path="sources" element={<SourcesPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
