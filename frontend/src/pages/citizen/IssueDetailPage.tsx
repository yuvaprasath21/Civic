import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { MapPin, Star, Send, Sparkles } from "lucide-react";
import clsx from "clsx";

import { CitizenLayout } from "@/layouts/CitizenLayout";
import { Button } from "@/components/common/Button";
import { useAuth } from "@/context/AuthContext";
import { ApiError } from "@/api/client";
import { issueService, IssueDetail } from "@/services/issueService";
import { resolveUploadUrl } from "@/services/profileService";
import { CATEGORY_LABELS, STATUS_COLORS, STATUS_LABELS, SEVERITY_COLORS, SEVERITY_LABELS } from "@/utils/issueDisplay";

const EDITABLE_STATUSES = new Set(["REPORTED", "AI_ANALYZED"]);
const FEEDBACK_ELIGIBLE_STATUSES = new Set(["RESOLVED", "CLOSED"]);

function DetailSkeleton() {
  return (
    <div className="max-w-3xl space-y-4 animate-pulse">
      <div className="h-8 w-2/3 bg-slate-200 rounded" />
      <div className="h-64 bg-slate-200 rounded-xl" />
      <div className="h-32 bg-slate-200 rounded-xl" />
    </div>
  );
}

export default function IssueDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();

  const [issue, setIssue] = useState<IssueDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [commentBody, setCommentBody] = useState("");
  const [isPostingComment, setIsPostingComment] = useState(false);

  const [feedbackRating, setFeedbackRating] = useState(0);
  const [feedbackComment, setFeedbackComment] = useState("");
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);

  const load = () => {
    if (!id) return;
    setIsLoading(true);
    issueService.getIssue(id)
      .then(setIssue)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load issue."))
      .finally(() => setIsLoading(false));
  };

  useEffect(load, [id]);

  const isOwner = !!(issue && user && issue.reporter_id === user.id);
  const canEdit = isOwner && issue && EDITABLE_STATUSES.has(issue.status);
  const canLeaveFeedback = isOwner && issue && FEEDBACK_ELIGIBLE_STATUSES.has(issue.status) && !issue.feedback;

  const submitComment = async () => {
    if (!id || !commentBody.trim()) return;
    setIsPostingComment(true);
    try {
      await issueService.addComment(id, commentBody.trim());
      setCommentBody("");
      load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to post comment.");
    } finally {
      setIsPostingComment(false);
    }
  };

  const submitFeedback = async () => {
    if (!id || feedbackRating === 0) return;
    setIsSubmittingFeedback(true);
    try {
      await issueService.addFeedback(id, feedbackRating, feedbackComment.trim() || undefined);
      toast.success("Thanks for the feedback!");
      load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to submit feedback.");
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  return (
    <CitizenLayout>
      {isLoading && <DetailSkeleton />}
      {!isLoading && error && (
        <div className="max-w-3xl rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      {!isLoading && issue && (
        <div className="max-w-3xl">
          <div className="flex items-start justify-between gap-4 mb-1">
            <h1 className="text-2xl font-semibold text-slate-900">{issue.title}</h1>
            <span className="text-sm text-slate-400 whitespace-nowrap">{issue.reference_code}</span>
          </div>
          <div className="flex items-center gap-2 mb-6">
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_COLORS[issue.status]}`}>{STATUS_LABELS[issue.status]}</span>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${SEVERITY_COLORS[issue.severity]}`}>{SEVERITY_LABELS[issue.severity]}</span>
            <span className="text-xs text-slate-400">{CATEGORY_LABELS[issue.category]}</span>
          </div>

          {issue.master_reference_code && (
            <div className="mb-6 rounded-lg border border-purple-200 bg-purple-50 px-4 py-3 text-sm text-purple-800">
              {issue.status === "CLOSED"
                ? <>This report was merged into <Link to={`/issues/${issue.master_issue_id}`} className="font-medium underline">{issue.master_reference_code}</Link>. You&apos;ll see progress on that issue.</>
                : <>This looks like a duplicate of <Link to={`/issues/${issue.master_issue_id}`} className="font-medium underline">{issue.master_reference_code}</Link>. An administrator will confirm shortly.</>}
            </div>
          )}
          {!issue.master_reference_code && issue.report_count > 1 && (
            <div className="mb-6 rounded-lg border border-brand-100 bg-brand-50 px-4 py-3 text-sm text-brand-800">
              {issue.report_count} citizens have reported this issue, which raises its priority.
            </div>
          )}

          {issue.assigned_to_name && (
            <div className="mb-6 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              <p>Assigned to <span className="font-medium">{issue.assigned_to_name}</span></p>
              {issue.status === "IN_PROGRESS" && typeof issue.progress_percent === "number" && (
                <div className="mt-2">
                  <div className="h-2 w-full rounded-full bg-emerald-100 overflow-hidden">
                    <div className="h-full bg-emerald-500" style={{ width: `${issue.progress_percent}%` }} />
                  </div>
                  <p className="text-xs mt-1">{issue.progress_percent}% complete</p>
                </div>
              )}
            </div>
          )}

          {issue.images.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-6">
              {issue.images.map((img) => (
                <a key={img.id} href={resolveUploadUrl(img.url)} target="_blank" rel="noreferrer">
                  <img src={resolveUploadUrl(img.url)} alt="" className="aspect-square w-full object-cover rounded-lg border border-slate-200" />
                </a>
              ))}
            </div>
          )}

          {issue.description && <p className="text-sm text-slate-600 mb-6">{issue.description}</p>}

          <div className="flex items-start gap-2 text-sm text-slate-500 mb-8">
            <MapPin className="h-4 w-4 mt-0.5 shrink-0" />
            <span>
              {issue.location.address_text || `${issue.location.latitude.toFixed(5)}, ${issue.location.longitude.toFixed(5)}`}
              {issue.location.city && ` · ${issue.location.city}`}
            </span>
          </div>

          {issue.ai_prediction && (
            <div className="mb-8 rounded-xl border border-brand-100 bg-brand-50/50 p-5">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="h-4 w-4 text-brand-600" />
                <h2 className="text-sm font-semibold text-slate-900">AI analysis</h2>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
                <div><p className="text-slate-500">Detected category</p><p className="font-medium text-slate-800">{CATEGORY_LABELS[issue.ai_prediction.category]}</p></div>
                <div><p className="text-slate-500">Confidence</p><p className="font-medium text-slate-800">{Math.round(issue.ai_prediction.confidence * 100)}%</p></div>
                <div><p className="text-slate-500">Suggested severity</p><p className="font-medium text-slate-800">{SEVERITY_LABELS[issue.ai_prediction.severity]}</p></div>
              </div>
              {issue.is_citizen_edited_category && <p className="text-xs text-brand-700 mt-3">You selected a different category than the AI suggested.</p>}
            </div>
          )}

          {/* --- Priority --- */}
          <div className="mb-8 flex items-center gap-4 rounded-xl border border-slate-200 p-4 text-sm">
            <div><p className="text-slate-500">Priority score</p><p className="font-medium text-slate-800">{issue.priority_score.toFixed(0)} / 100</p></div>
            <div><p className="text-slate-500">Priority level</p><p className="font-medium text-slate-800">{issue.priority_level}</p></div>
          </div>

          {canEdit && (
            <div className="mb-8 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              You can still edit this report — it hasn't been verified yet.
            </div>
          )}

          <div className="mb-8">
            <h2 className="text-sm font-semibold text-slate-900 mb-3">Timeline</h2>
            <ol className="space-y-4 border-l-2 border-slate-100 pl-4">
              {issue.status_history.map((entry, idx) => (
                <li key={idx} className="relative">
                  <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-brand-500" />
                  <p className="text-sm font-medium text-slate-800">{STATUS_LABELS[entry.to_status]}</p>
                  {entry.note && <p className="text-sm text-slate-500">{entry.note}</p>}
                  <p className="text-xs text-slate-400 mt-0.5">
                    {new Date(entry.created_at).toLocaleString()}{entry.changed_by_name && ` · ${entry.changed_by_name}`}
                  </p>
                </li>
              ))}
            </ol>
          </div>

          {canLeaveFeedback && (
            <div className="mb-8 rounded-xl border border-slate-200 p-5">
              <h2 className="text-sm font-semibold text-slate-900 mb-3">How was the resolution?</h2>
              <div className="flex gap-1 mb-3">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button key={n} type="button" onClick={() => setFeedbackRating(n)}>
                    <Star className={clsx("h-6 w-6", n <= feedbackRating ? "fill-amber-400 text-amber-400" : "text-slate-300")} />
                  </button>
                ))}
              </div>
              <textarea rows={2} placeholder="Optional comment" value={feedbackComment} onChange={(e) => setFeedbackComment(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500" />
              <Button onClick={submitFeedback} isLoading={isSubmittingFeedback} disabled={feedbackRating === 0}>Submit feedback</Button>
            </div>
          )}

          {issue.feedback && (
            <div className="mb-8 rounded-xl border border-emerald-200 bg-emerald-50 p-5">
              <p className="text-sm font-medium text-emerald-800 mb-1">Your feedback</p>
              <div className="flex gap-0.5 mb-1">
                {[1, 2, 3, 4, 5].map((n) => (
                  <Star key={n} className={clsx("h-4 w-4", n <= issue.feedback!.rating ? "fill-amber-400 text-amber-400" : "text-slate-300")} />
                ))}
              </div>
              {issue.feedback.comment && <p className="text-sm text-emerald-700">{issue.feedback.comment}</p>}
            </div>
          )}

          <div>
            <h2 className="text-sm font-semibold text-slate-900 mb-3">Comments {issue.comments.length > 0 && `(${issue.comments.length})`}</h2>
            <div className="space-y-4 mb-4">
              {issue.comments.filter((c) => !c.is_internal).map((c) => (
                <div key={c.id} className="flex gap-3">
                  <div className="h-8 w-8 shrink-0 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-xs font-semibold">
                    {c.author_name[0]?.toUpperCase()}
                  </div>
                  <div>
                    <p className="text-sm"><span className="font-medium text-slate-800">{c.author_name}</span> <span className="text-xs text-slate-400">{new Date(c.created_at).toLocaleString()}</span></p>
                    <p className="text-sm text-slate-600">{c.body}</p>
                  </div>
                </div>
              ))}
              {issue.comments.filter((c) => !c.is_internal).length === 0 && <p className="text-sm text-slate-400">No comments yet.</p>}
            </div>
            <div className="flex gap-2">
              <input type="text" value={commentBody} onChange={(e) => setCommentBody(e.target.value)} placeholder="Add a comment..."
                className="flex-1 rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500"
                onKeyDown={(e) => e.key === "Enter" && submitComment()} />
              <Button onClick={submitComment} isLoading={isPostingComment} disabled={!commentBody.trim()}><Send className="h-4 w-4" /></Button>
            </div>
          </div>
        </div>
      )}
    </CitizenLayout>
  );
}
