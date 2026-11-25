import { Routes, Route, Link } from "react-router-dom";

import LoginPage from "@/pages/auth/LoginPage";
import RegisterPage from "@/pages/auth/RegisterPage";
import ForgotPasswordPage from "@/pages/auth/ForgotPasswordPage";
import ResetPasswordPage from "@/pages/auth/ResetPasswordPage";
import VerifyContactPage from "@/pages/auth/VerifyContactPage";
import CitizenDashboardPage from "@/pages/citizen/CitizenDashboardPage";
import ProfilePage from "@/pages/citizen/ProfilePage";
import ReportIssuePage from "@/pages/citizen/ReportIssuePage";
import IssuesListPage from "@/pages/citizen/IssuesListPage";
import IssueDetailPage from "@/pages/citizen/IssueDetailPage";
import NearbyIssuesPage from "@/pages/citizen/NearbyIssuesPage";
import StaffDashboardPage from "@/pages/staff/StaffDashboardPage";
import StaffIssuesPage from "@/pages/staff/StaffIssuesPage";
import StaffIssueDetailPage from "@/pages/staff/StaffIssueDetailPage";
import StaffProfilePage from "@/pages/staff/StaffProfilePage";
import AdminDashboardPage from "@/pages/admin/AdminDashboardPage";
import { ProtectedRoute } from "@/routes/ProtectedRoute";

function LandingPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="text-center px-6">
        <div className="inline-flex items-center gap-2 mb-4">
          <span className="h-2.5 w-2.5 rounded-full bg-brand-500" />
          <span className="text-sm font-medium tracking-wide text-brand-700 uppercase">CivicPulse</span>
        </div>
        <h1 className="text-3xl font-semibold text-slate-900 mb-2">Smart Civic Issue Management System</h1>
        <p className="text-slate-500 max-w-md mx-auto mb-6">
          Report civic issues, track their resolution, and see AI-assisted prioritization in action.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Link to="/login" className="rounded-lg bg-brand-600 text-white px-4 py-2.5 text-sm font-medium hover:bg-brand-700">Sign in</Link>
          <Link to="/register" className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50">Create account</Link>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/verify-contact" element={<VerifyContactPage />} />

      <Route path="/dashboard" element={<ProtectedRoute allowedRoles={["CITIZEN"]}><CitizenDashboardPage /></ProtectedRoute>} />
      <Route path="/profile" element={<ProtectedRoute allowedRoles={["CITIZEN"]}><ProfilePage /></ProtectedRoute>} />
      <Route path="/report-issue" element={<ProtectedRoute allowedRoles={["CITIZEN"]}><ReportIssuePage /></ProtectedRoute>} />
      <Route path="/issues" element={<ProtectedRoute allowedRoles={["CITIZEN"]}><IssuesListPage /></ProtectedRoute>} />
      <Route path="/issues/:id" element={<ProtectedRoute allowedRoles={["CITIZEN"]}><IssueDetailPage /></ProtectedRoute>} />
      <Route path="/nearby-issues" element={<ProtectedRoute allowedRoles={["CITIZEN"]}><NearbyIssuesPage /></ProtectedRoute>} />

      <Route path="/staff/dashboard" element={<ProtectedRoute allowedRoles={["FIELD_STAFF"]}><StaffDashboardPage /></ProtectedRoute>} />
      <Route path="/staff/issues" element={<ProtectedRoute allowedRoles={["FIELD_STAFF"]}><StaffIssuesPage /></ProtectedRoute>} />
      <Route path="/staff/issues/:id" element={<ProtectedRoute allowedRoles={["FIELD_STAFF"]}><StaffIssueDetailPage /></ProtectedRoute>} />
      <Route path="/staff/profile" element={<ProtectedRoute allowedRoles={["FIELD_STAFF"]}><StaffProfilePage /></ProtectedRoute>} />
      <Route path="/admin/dashboard" element={<ProtectedRoute allowedRoles={["DEPARTMENT_ADMIN", "SUPER_ADMIN"]}><AdminDashboardPage /></ProtectedRoute>} />
    </Routes>
  );
}
