import { Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "./pages/login/page";
import RegisterPage from "./pages/register/page";
import Page from "./pages/dashboard/page";
import { SidebarInset, SidebarProvider } from "./components/ui/sidebar";
import { AppSidebar } from "./components/app-sidebar";
import Navbar from "./components/navbar";
import FavoritPage from "./pages/favorite/page";
import LandingPage from "./pages/landing/page";
import { Searchpage } from "./pages/search/search";
import DetailPublicationPage from "./pages/detail/pages"; // ← tambah ini

export function DashboardLayout({ children }: any) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="p-0 m-0 w-full max-w-none bg-background">
        <Navbar />
        <div className="p-4">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  );
}

function ProtectedRoute({ children }: any) {
  const token = localStorage.getItem("token");
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

function PublicRoute({ children }: any) {
  const token = localStorage.getItem("token");
  if (token) return <Navigate to="/search" replace />;
  return children;
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
      <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />
      <Route
        path="/dashboard"
        element={<ProtectedRoute><DashboardLayout><Page /></DashboardLayout></ProtectedRoute>}
      />
      <Route
        path="/search"
        element={<ProtectedRoute><DashboardLayout><Searchpage /></DashboardLayout></ProtectedRoute>}
      />
      <Route
        path="/favorite"
        element={<ProtectedRoute><DashboardLayout><FavoritPage /></DashboardLayout></ProtectedRoute>}
      />
      <Route
        path="/detail/:id"
        element={<ProtectedRoute><DashboardLayout><DetailPublicationPage /></DashboardLayout></ProtectedRoute>}
      />  {/* ← dipindah ke DALAM Routes */}
    </Routes>
  );
}

export default App;