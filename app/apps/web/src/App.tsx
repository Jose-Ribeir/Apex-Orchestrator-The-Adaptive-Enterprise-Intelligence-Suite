import AgentDocumentsPage from "@/app/(app)/agents/[agentId]/documents/page";
import AgentInstructionsPage from "@/app/(app)/agents/[agentId]/instructions/page";
import AgentIdLayout from "@/app/(app)/agents/[agentId]/layout";
import AgentPromptPage from "@/app/(app)/agents/[agentId]/prompt/page";
import AgentQueriesPage from "@/app/(app)/agents/[agentId]/queries/page";
import AgentStatsPage from "@/app/(app)/agents/[agentId]/stats/page";
import AgentToolsPage from "@/app/(app)/agents/[agentId]/tools/page";
import HumanTaskDetailPage from "@/app/(app)/human-tasks/[taskId]/page";
import HumanTasksPage from "@/app/(app)/human-tasks/page";
import NotificationsPage from "@/app/(app)/notifications/page";
import DashboardPage from "@/app/(app)/page";
import SettingsAgentsPage from "@/app/(app)/settings/agents/page";
import ApiTokensPage from "@/app/(app)/settings/api-tokens/page";
import ConnectionsPage from "@/app/(app)/settings/connections/page";
import ToolsPage from "@/app/(app)/tools/page";
import OnboardingPage from "@/app/onboarding/page";
import { LoginForm } from "@/components/login-form";
import { SignUpForm } from "@/components/signup-form";
import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { AppLayout } from "./layouts/AppLayout";
import { AuthLayout } from "./layouts/AuthLayout";
import { OnboardingLayout } from "./layouts/OnboardingLayout";

function AgentIdRouteWrapper() {
  return (
    <AgentIdLayout>
      <Outlet />
    </AgentIdLayout>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<AuthLayout />} path="auth">
        <Route element={<LoginForm />} path="sign-in" />
        <Route element={<SignUpForm />} path="sign-up" />
      </Route>
      <Route element={<OnboardingLayout />} path="onboarding">
        <Route index element={<OnboardingPage />} />
      </Route>
      <Route element={<AppLayout />} path="/">
        <Route index element={<DashboardPage />} />
        <Route element={<HumanTasksPage />} path="human-tasks" />
        <Route element={<HumanTaskDetailPage />} path="human-tasks/:taskId" />
        <Route element={<ConnectionsPage />} path="settings/connections" />
        <Route element={<NotificationsPage />} path="notifications" />
        <Route element={<ToolsPage />} path="tools" />
        <Route
          element={<Navigate to="/settings/api-tokens" replace />}
          path="settings"
        />
        <Route element={<ApiTokensPage />} path="settings/api-tokens" />
        <Route element={<SettingsAgentsPage />} path="settings/agents" />
        <Route element={<AgentIdRouteWrapper />} path="agents/:agentId">
          <Route index element={<Navigate to="instructions" replace />} />
          <Route element={<AgentInstructionsPage />} path="instructions" />
          <Route element={<AgentPromptPage />} path="prompt" />
          <Route element={<AgentDocumentsPage />} path="documents" />
          <Route element={<AgentToolsPage />} path="tools" />
          <Route element={<AgentQueriesPage />} path="queries" />
          <Route element={<AgentStatsPage />} path="stats" />
        </Route>
      </Route>
    </Routes>
  );
}
