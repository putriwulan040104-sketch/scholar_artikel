import { Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { isSuperAdmin } from "./api/api";
import { AppSidebar } from "./components/app-sidebar";
import Navbar from "./components/navbar";
import { SidebarInset, SidebarProvider } from "./components/ui/sidebar";
import Page from "./pages/dashboard/page";
import DetailPublicationPage from "./pages/detail/pages";
import FavoritPage from "./pages/favorite/page";
import LandingPage from "./pages/landing/page";
import LoginPage from "./pages/login/page";
import CitationGraphPage from "./pages/citation-graph/page";
import RegisterPage from "./pages/register/page";
import { Searchpage } from "./pages/search/search";
import SuperAdminDashboardPage from "./pages/super-admin/dashboard/page";
import SuperAdminRequestsPage from "./pages/super-admin/requests/page";
import SuperAdminUsersPage from "./pages/super-admin/users/page";
import SuperAdminPublicationsPage from "./pages/super-admin/publications/page";
import SuperAdminActivityLogsPage from "./pages/super-admin/activity-logs/page";

export function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="m-0 min-w-0 w-0 flex-1 max-w-full bg-background p-0">
        <Navbar />
        <div className="min-w-0 max-w-full overflow-x-hidden p-4">
          {children}
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}

function ProtectedRoute({ children }: { children: ReactNode }) {
  const token = localStorage.getItem("token");
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function PublicRoute({ children }: { children: ReactNode }) {
  const token = localStorage.getItem("token");
  if (token) return <Navigate to="/search" replace />;
  return <>{children}</>;
}

function SuperAdminRoute({ children }: { children: ReactNode }) {
  const token = localStorage.getItem("token");
  if (!token) return <Navigate to="/login" replace />;
  if (!isSuperAdmin()) return <Navigate to="/search" replace />;
  return <>{children}</>;
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route
        path="/login"
        element={
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        }
      />
      <Route
        path="/register"
        element={
          <PublicRoute>
            <RegisterPage />
          </PublicRoute>
        }
      />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardLayout>
              <Page />
            </DashboardLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/search"
        element={
          <ProtectedRoute>
            <DashboardLayout>
              <Searchpage />
            </DashboardLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/favorite"
        element={
          <ProtectedRoute>
            <DashboardLayout>
              <FavoritPage />
            </DashboardLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/citation-graph"
        element={
          <ProtectedRoute>
            <DashboardLayout>
              <CitationGraphPage />
            </DashboardLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/detail/:id"
        element={
          <ProtectedRoute>
            <DashboardLayout>
              <DetailPublicationPage />
            </DashboardLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/super-admin/dashboard"
        element={
          <SuperAdminRoute>
            <DashboardLayout>
              <SuperAdminDashboardPage />
            </DashboardLayout>
          </SuperAdminRoute>
        }
      />
      <Route
        path="/super-admin/users"
        element={
          <SuperAdminRoute>
            <DashboardLayout>
              <SuperAdminUsersPage />
            </DashboardLayout>
          </SuperAdminRoute>
        }
      />
      <Route
        path="/super-admin/requests"
        element={
          <SuperAdminRoute>
            <DashboardLayout>
              <SuperAdminRequestsPage />
            </DashboardLayout>
          </SuperAdminRoute>
        }
      />
      <Route
        path="/super-admin/publications"
        element={
          <SuperAdminRoute>
            <DashboardLayout>
              <SuperAdminPublicationsPage />
            </DashboardLayout>
          </SuperAdminRoute>
        }
      />
      <Route
        path="/super-admin/activity-logs"
        element={
          <SuperAdminRoute>
            <DashboardLayout>
              <SuperAdminActivityLogsPage />
            </DashboardLayout>
          </SuperAdminRoute>
        }
      />
    </Routes>
  );
}

export default App;
