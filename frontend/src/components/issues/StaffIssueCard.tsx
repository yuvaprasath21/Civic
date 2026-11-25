import { Link } from "react-router-dom";
import { MapPin } from "lucide-react";
import { resolveUploadUrl } from "@/services/profileService";
import type { StaffIssueSummary } from "@/services/staffService";
import { CATEGORY_LABELS, PRIORITY_COLORS, STATUS_COLORS, STATUS_LABELS } from "@/utils/issueDisplay";

export function StaffIssueCard({ issue }: { issue: StaffIssueSummary }) {
  return (
    <Link to={`/staff/issues/${issue.id}`}
      className="flex gap-4 rounded-xl border border-slate-200 bg-white p-4 hover:border-emerald-300 hover:shadow-sm transition-all">
      <div className="h-20 w-20 shrink-0 rounded-lg overflow-hidden bg-slate-100">
        {issue.thumbnail_url ? (
          <img src={resolveUploadUrl(issue.thumbnail_url)} alt={issue.title} className="h-full w-full object-cover" />
        ) : (
          <div className="h-full w-full flex items-center justify-center text-slate-300 text-xs">No photo</div>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-medium text-slate-900 truncate">{issue.title}</p>
          <span className="text-xs text-slate-400 whitespace-nowrap shrink-0">{issue.reference_code}</span>
        </div>
        <p className="text-xs text-slate-500 mt-0.5">{CATEGORY_LABELS[issue.category]}</p>
        {(issue.location.address_text || issue.location.city) && (
          <p className="flex items-center gap-1 text-xs text-slate-400 mt-1 truncate">
            <MapPin className="h-3 w-3 shrink-0" />{issue.location.address_text ?? issue.location.city}
          </p>
        )}
        <div className="flex flex-wrap items-center gap-2 mt-2">
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${PRIORITY_COLORS[issue.priority_level]}`}>
            {issue.priority_level} · {Math.round(issue.priority_score)}
          </span>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_COLORS[issue.status]}`}>{STATUS_LABELS[issue.status]}</span>
          {issue.assignment_status === "IN_PROGRESS" && <span className="text-xs text-slate-500">{issue.progress_percent}% done</span>}
        </div>
      </div>
    </Link>
  );
}
