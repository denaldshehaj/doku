/* Route table. Every page is lazy-loaded so each route becomes its own chunk
 * (code splitting along the natural boundary). */
import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { Spinner } from "@/components/ui/misc";
import {
  RedirectIfAuthenticated, RequireAdmin, RequireAuth, RequirePasswordChange,
} from "@/routes/guards";

const LoginPage = lazy(() => import("@/features/auth/LoginPage"));
const ChangePasswordPage = lazy(() => import("@/features/auth/ChangePasswordPage"));
const DashboardPage = lazy(() => import("@/features/dashboard/DashboardPage"));
const ChatPage = lazy(() => import("@/features/chat/ChatPage"));
const SummariesPage = lazy(() => import("@/features/summaries/SummariesPage"));
const HistoryPage = lazy(() => import("@/features/history/HistoryPage"));
const DocumentsPage = lazy(() => import("@/features/admin/documents/DocumentsPage"));
const UsersPage = lazy(() => import("@/features/admin/users/UsersPage"));
const AuditPage = lazy(() => import("@/features/admin/audit/AuditPage"));
const ExperimentsPage = lazy(() => import("@/features/admin/experiments/ExperimentsPage"));
const ReportsPage = lazy(() => import("@/features/admin/reports/ReportsPage"));

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div className="flex h-full items-center justify-center"><Spinner /></div>}>
        <Routes>
          <Route path="/login"
                 element={<RedirectIfAuthenticated><LoginPage /></RedirectIfAuthenticated>} />
          <Route path="/ndrysho-fjalekalimin"
                 element={<RequirePasswordChange><ChangePasswordPage /></RequirePasswordChange>} />

          <Route element={<RequireAuth><AppShell /></RequireAuth>}>
            <Route index element={<DashboardPage />} />
            <Route path="biseda" element={<ChatPage />} />
            <Route path="permbledhje" element={<SummariesPage />} />
            <Route path="historiku" element={<HistoryPage />} />

            <Route path="admin" element={<RequireAdmin />}>
              <Route path="dokumentet" element={<DocumentsPage />} />
              <Route path="perdoruesit" element={<UsersPage />} />
              <Route path="raportet" element={<ReportsPage />} />
              <Route path="audit" element={<AuditPage />} />
              <Route path="eksperimentet" element={<ExperimentsPage />} />
            </Route>

            {/* Unknown paths land on the dashboard. */}
            <Route path="*" element={<DashboardPage />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
