import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/common/Button";

export default function AdminDashboardPage() {
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">Admin dashboard</h1>
            <p className="text-slate-500 text-sm mt-1">Metrics, charts, issue and staff management arrive in Phase 9.</p>
          </div>
          <Button variant="secondary" onClick={logout}>Sign out</Button>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
          Signed in as <span className="font-medium text-slate-700">{user?.email}</span> ({user?.role}).
        </div>
      </div>
    </div>
  );
}
