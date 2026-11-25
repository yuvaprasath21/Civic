import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FileWarning, Plus } from "lucide-react";
import { CitizenLayout } from "@/layouts/CitizenLayout";
import { IssueCard } from "@/components/issues/IssueCard";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/common/Button";
import { issueService, IssueSummary } from "@/services/issueService";
import { CATEGORY_OPTIONS, STATUS_LABELS } from "@/utils/issueDisplay";
import type { IssueCategory, IssueStatus } from "@/types/domain";
import { ApiError } from "@/api/client";

function ListSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-24 rounded-xl bg-slate-100 animate-pulse" />)}
    </div>
  );
}

export default function IssuesListPage() {
  const [issues, setIssues] = useState<IssueSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState<IssueCategory | "">("");
  const [status, setStatus] = useState<IssueStatus | "">("");

  useEffect(() => {
    setIsLoading(true);
    issueService.listMyIssues({ category: category || undefined, status: status || undefined, page_size: 50 })
      .then((result) => { setIssues(result.items); setTotal(result.total); })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load issues."))
      .finally(() => setIsLoading(false));
  }, [category, status]);

  return (
    <CitizenLayout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">My issues</h1>
          <p className="text-slate-500 text-sm mt-1">{total} report{total === 1 ? "" : "s"} submitted</p>
        </div>
        <Link to="/report-issue">
          <Button><Plus className="h-4 w-4" />Report issue</Button>
        </Link>
      </div>

      <div className="flex gap-3 mb-6">
        <select value={category} onChange={(e) => setCategory(e.target.value as IssueCategory | "")} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700">
          <option value="">All categories</option>
          {CATEGORY_OPTIONS.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value as IssueStatus | "")} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700">
          <option value="">All statuses</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </div>

      {isLoading && <ListSkeleton />}
      {!isLoading && error && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      {!isLoading && !error && issues.length === 0 && (
        <EmptyState icon={<FileWarning className="h-10 w-10" />} title="No issues found"
          description="Nothing matches these filters yet. Try clearing them, or report a new issue."
          action={<Link to="/report-issue"><Button variant="secondary">Report an issue</Button></Link>} />
      )}
      {!isLoading && !error && issues.length > 0 && (
        <div className="space-y-3">{issues.map((issue) => <IssueCard key={issue.id} issue={issue} />)}</div>
      )}
    </CitizenLayout>
  );
}
