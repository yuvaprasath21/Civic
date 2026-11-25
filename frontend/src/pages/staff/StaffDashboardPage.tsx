import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { StaffLayout } from "@/layouts/StaffLayout";
import { StaffIssueCard } from "@/components/issues/StaffIssueCard";
import { EmptyState } from "@/components/common/EmptyState";
import { useAuth } from "@/context/AuthContext";
import { ApiError } from "@/api/client";
import { staffService, StaffIssueSummary, StaffStats } from "@/services/staffService";
import { ClipboardCheck } from "lucide-react";

export default function StaffDashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<StaffStats | null>(null);
  const [issues, setIssues] = useState<StaffIssueSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([staffService.stats(), staffService.listIssues({ page_size: 5 })])
      .then(([s, list]) => { setStats(s); setIssues(list.items); })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load your dashboard."))
      .finally(() => setLoading(false));
  }, []);

  const cards = stats && [
    { label: "To accept", value: stats.pending },
    { label: "Accepted", value: stats.accepted },
    { label: "In progress", value: stats.in_progress },
    { label: "Resolved (all time)", value: stats.total_resolved },
  ];

  return (
    <StaffLayout>
      <h1 className="text-2xl font-semibold text-slate-900 mb-1">Hello, {user?.full_name.split(" ")[0]}</h1>
      <p className="text-slate-500 text-sm mb-8">
        {stats?.department_name ? `${stats.department_name} · ` : ""}Your most urgent assignments are listed first.
      </p>

      {error && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 mb-6">{error}</div>}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-24 rounded-xl bg-slate-100 animate-pulse" />)
          : cards?.map((c) => (
              <div key={c.label} className="rounded-xl border border-slate-200 bg-white p-5">
                <p className="text-sm text-slate-500">{c.label}</p>
                <p className="text-2xl font-semibold text-slate-900 mt-1">{c.value}</p>
              </div>
            ))}
      </div>

      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-slate-900">Top priority</h2>
        <Link to="/staff/issues" className="text-sm text-emerald-700 hover:text-emerald-800">View all</Link>
      </div>
      {!loading && issues.length === 0 && !error && (
        <EmptyState icon={<ClipboardCheck className="h-10 w-10" />} title="Nothing assigned right now" description="New assignments from your department admin will appear here." />
      )}
      <div className="space-y-3">{issues.map((i) => <StaffIssueCard key={i.id} issue={i} />)}</div>
    </StaffLayout>
  );
}
