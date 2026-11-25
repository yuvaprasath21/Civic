import { useEffect, useState } from "react";
import clsx from "clsx";
import { ClipboardList } from "lucide-react";
import { StaffLayout } from "@/layouts/StaffLayout";
import { StaffIssueCard } from "@/components/issues/StaffIssueCard";
import { EmptyState } from "@/components/common/EmptyState";
import { ApiError } from "@/api/client";
import { staffService, StaffIssueSummary } from "@/services/staffService";
import type { PriorityLevel } from "@/types/domain";

type Tab = "active" | "history";
const PRIORITIES: PriorityLevel[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

export default function StaffIssuesPage() {
  const [tab, setTab] = useState<Tab>("active");
  const [priority, setPriority] = useState<PriorityLevel | "">("");
  const [issues, setIssues] = useState<StaffIssueSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const request = tab === "active"
      ? staffService.listIssues({ priority: priority || undefined, page_size: 50 })
      : staffService.history({ page_size: 50 });
    request
      .then((r) => { setIssues(r.items); setTotal(r.total); })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load assignments."))
      .finally(() => setLoading(false));
  }, [tab, priority]);

  return (
    <StaffLayout>
      <h1 className="text-2xl font-semibold text-slate-900 mb-1">My assignments</h1>
      <p className="text-slate-500 text-sm mb-6">{total} {tab === "active" ? "active" : "past"} assignment{total === 1 ? "" : "s"}</p>

      <div className="flex items-center justify-between mb-6 gap-4">
        <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1">
          {(["active", "history"] as Tab[]).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={clsx("px-4 py-1.5 text-sm font-medium rounded-md", tab === t ? "bg-emerald-600 text-white" : "text-slate-600 hover:text-slate-900")}>
              {t === "active" ? "Active" : "Work history"}
            </button>
          ))}
        </div>
        {tab === "active" && (
          <select value={priority} onChange={(e) => setPriority(e.target.value as PriorityLevel | "")}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700">
            <option value="">All priorities</option>
            {PRIORITIES.map((p) => <option key={p} value={p}>{p[0] + p.slice(1).toLowerCase()}</option>)}
          </select>
        )}
      </div>

      {loading && <div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-24 rounded-xl bg-slate-100 animate-pulse" />)}</div>}
      {!loading && error && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      {!loading && !error && issues.length === 0 && (
        <EmptyState icon={<ClipboardList className="h-10 w-10" />} title={tab === "active" ? "No active assignments" : "No completed work yet"}
          description={priority ? "Nothing matches this priority. Try clearing the filter." : undefined} />
      )}
      {!loading && !error && <div className="space-y-3">{issues.map((i) => <StaffIssueCard key={i.id} issue={i} />)}</div>}
    </StaffLayout>
  );
}
