import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { RequireHousehold } from "./components/layout/RequireHousehold";
import { HouseholdProvider } from "./context/HouseholdContext";
import { ToastProvider } from "./context/ToastContext";
import { ErrorBoundary } from "./ErrorBoundary";
import { BillsPage } from "./pages/BillsPage";
import { ChatPage } from "./pages/ChatPage";
import { ChoresPage } from "./pages/ChoresPage";
import { CreateHouseholdPage } from "./pages/CreateHouseholdPage";
import { DashboardPage } from "./pages/DashboardPage";
import { GroceriesPage } from "./pages/GroceriesPage";
import { JoinHouseholdPage } from "./pages/JoinHouseholdPage";
import { LandingPage } from "./pages/LandingPage";
import { MembersPage } from "./pages/MembersPage";
import { SettingsPage } from "./pages/SettingsPage";

export default function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <HouseholdProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/create" element={<CreateHouseholdPage />} />
              <Route path="/join" element={<JoinHouseholdPage />} />

              {/* Trailing "*" is required: without it the parent stops matching on
                  deeper paths and every in-app route falls through to the catch-all. */}
              <Route
                path="/app/*"
                element={
                  <RequireHousehold>
                    <AppShell>
                      <Routes>
                        <Route index element={<DashboardPage />} />
                        <Route path="chat" element={<ChatPage />} />
                        <Route path="chores" element={<ChoresPage />} />
                        <Route path="bills" element={<BillsPage />} />
                        <Route path="groceries" element={<GroceriesPage />} />
                        <Route path="members" element={<MembersPage />} />
                        <Route path="settings" element={<SettingsPage />} />
                        <Route path="*" element={<Navigate to="/app" replace />} />
                      </Routes>
                    </AppShell>
                  </RequireHousehold>
                }
              />

              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </HouseholdProvider>
      </ToastProvider>
    </ErrorBoundary>
  );
}
